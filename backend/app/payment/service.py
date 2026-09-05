import uuid
from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.order import Cart, CartItem, Order, OrderItem, Payment
from app.models.offer import Offer
from app.models.webhook import WebhookEvent
from app.models.audit import AuditLog
from app.policy.service import PolicyService
from app.policy.schemas import PolicyEvaluationRequest
from app.payment.razorpay_client import (
    create_order as create_rp_order,
    verify_payment_signature,
    charge_saved_instrument,
    capture_payment as capture_rp_payment,
    fetch_payment as fetch_rp_payment,
    RAZORPAY_KEY_ID
)
from app.payment.exceptions import (
    PaymentStateError, AmountMismatchError, AgentAuthorizationError,
    TransactionLimitExceeded, DailyLimitExceeded, InsufficientInventory,
    MerchantInactive, RazorpayProviderError, SpendingLimitNotConfigured,
    SavedInstrumentInvalid, ChargeDeclined
)

from app.payment.schemas import DirectCheckoutRequest

import logging
logger = logging.getLogger(__name__)


def authorize_agentic_purchase(db: Session, merchant_id: str, customer_id: str, total_amount: Decimal, items: list, human_approval: bool):
    """
    Enforces strict agentic payment bounds.
    Returns a dict with the limits that were checked against (for audit metadata).
    """
    # 1. Merchant validation
    from app.models.merchant import Merchant
    merchant = db.query(Merchant).filter(Merchant.id == merchant_id).first()
    if not merchant or not merchant.is_active:
        raise MerchantInactive(f"Merchant {merchant_id} is inactive or not found.")

    # 2. Authorization check (Mandate / Approval)
    if not human_approval:
        raise AgentAuthorizationError("Agent attempted to execute purchase without explicitly verified human authorization in this turn.")

    # 3. Transaction limit check
    from app.models.customer import Customer
    customer = db.query(Customer).filter(Customer.id == customer_id).first()

    # NULL means the customer has never explicitly configured a limit → block.
    if customer is None or customer.transaction_limit is None:
        raise SpendingLimitNotConfigured(
            "No spending limit configured. Please set a per-transaction limit in your settings before making purchases."
        )

    tx_limit = Decimal(str(customer.transaction_limit))
    daily_limit = Decimal(str(customer.daily_limit)) if customer.daily_limit is not None else Decimal('50000')

    if total_amount > tx_limit:
        raise TransactionLimitExceeded(
            f"Order total (₹{total_amount}) exceeds your per-transaction limit of ₹{tx_limit}."
        )

    # 4. Daily limit check
    from sqlalchemy import func
    today = datetime.utcnow().date()
    daily_total = db.query(func.sum(Payment.amount)).join(Order).filter(
        Order.customer_id == customer_id,
        Payment.status == "CAPTURED",
        func.date(Payment.created_at) == today
    ).scalar() or Decimal('0')

    if daily_total + total_amount > daily_limit:
        raise DailyLimitExceeded(
            f"This purchase (₹{total_amount}) would exceed your daily limit of ₹{daily_limit} "
            f"(today's total so far: ₹{daily_total})."
        )

    # 5. Inventory check
    from app.models.product import Inventory
    for item in items:
        if hasattr(item, 'offer_id') and item.offer_id:
            inv = db.query(Inventory).filter(Inventory.offer_id == item.offer_id).with_for_update().first()
            if not inv or inv.quantity < item.quantity:
                raise InsufficientInventory(f"Insufficient inventory for offer {item.offer_id}.")

    return {"tx_limit": str(tx_limit), "daily_limit": str(daily_limit), "daily_spent": str(daily_total)}


def create_direct_payment_order(db: Session, req: DirectCheckoutRequest) -> dict:
    # 1. Fetch offer and validate
    offer = db.query(Offer).filter(Offer.id == req.offer_id, Offer.product_id == req.product_id).first()
    if not offer:
        raise PaymentStateError("Offer not found or mismatch.")

    # 2. Create an ephemeral Cart for direct checkout
    cart = Cart(
        customer_id=req.customer_id,
        merchant_id=req.merchant_id,
        status="ACTIVE",
        currency="INR",
        discount=Decimal('0')
    )
    db.add(cart)
    db.flush()

    # 3. Add CartItem
    item = CartItem(
        cart_id=cart.id,
        offer_id=offer.id,
        quantity=req.quantity,
        unit_price=offer.price
    )
    db.add(item)
    db.flush()

    # 4. Delegate to the existing robust checkout engine
    try:
        limits = authorize_agentic_purchase(
            db, req.merchant_id, req.customer_id,
            offer.price * req.quantity, [item], req.human_approval
        )

        result = create_payment_order(
            db=db,
            merchant_id=req.merchant_id,
            customer_id=req.customer_id,
            cart_id=str(cart.id),
            source=req.source,
            agent_trace=req.agent_trace,
            human_approval=req.human_approval,
            skip_auth=True,  # already authorized above
            limits_checked=limits
        )
        return result
    except Exception as e:
        error_name = e.__class__.__name__
        audit = AuditLog(
            merchant_id=req.merchant_id,
            customer_id=req.customer_id,
            action=f"GATE_FAILED:{error_name}",
            event_type="payment",
            actor_type="SYSTEM",
            metadata_json={
                "reason": str(e),
                "amount": str(offer.price * req.quantity),
                "error_class": error_name
            }
        )
        db.add(audit)
        db.commit()
        raise


def create_payment_order(
    db: Session,
    merchant_id: str,
    customer_id: str,
    cart_id: str,
    source: str = "DIRECT",
    agent_trace: dict = None,
    human_approval: bool = False,
    skip_auth: bool = False,
    limits_checked: dict = None
) -> dict:
    # 1. Load the cart
    cart = db.query(Cart).filter(
        Cart.id == cart_id,
        Cart.customer_id == customer_id,
        Cart.merchant_id == merchant_id,
        Cart.status == "ACTIVE"
    ).first()
    if not cart:
        raise PaymentStateError("Cart not found or not active")

    # 2. Policy Engine
    policy_service = PolicyService(db)
    request = PolicyEvaluationRequest(
        merchant_id=merchant_id,
        customer_id=customer_id,
        cart_id=cart_id
    )
    decision = policy_service.evaluate(request).model_dump()

    if decision["decision"] == "REJECTED":
        raise PaymentStateError(f"Checkout rejected: {decision['reasons']}")
    if decision["decision"] == "REQUIRES_CONSENT":
        if not human_approval:
            raise PaymentStateError("Consent required: human approval is required for this purchase.")
        from app.models.consent import ConsentRequest
        consent = db.query(ConsentRequest).filter(
            ConsentRequest.cart_id == cart_id,
            ConsentRequest.status == "APPROVED"
        ).first()
        if not consent:
            raise PaymentStateError("Consent required but not approved")

    # 3. Calculate authoritative amount (always in rupees; convert to paise at the end)
    total = sum((item.offer.price * item.quantity) for item in cart.items if item.offer)
    discount = cart.discount or Decimal('0')
    total -= discount
    if total <= 0:
        raise PaymentStateError("Invalid cart total")

    amount_paise = int(total * 100)

    # Agentic Gates (if not skipped from direct checkout path)
    if not skip_auth:
        try:
            limits_checked = authorize_agentic_purchase(db, merchant_id, customer_id, total, cart.items, human_approval)
            audit = AuditLog(
                merchant_id=merchant_id,
                customer_id=customer_id,
                action="GATE_PASSED:CART_CHECKOUT",
                event_type="payment",
                actor_type="SYSTEM",
                metadata_json={
                    "amount": str(total),
                    "limit_checked": limits_checked
                }
            )
            db.add(audit)
        except Exception as e:
            error_name = e.__class__.__name__
            audit = AuditLog(
                merchant_id=merchant_id,
                customer_id=customer_id,
                action=f"GATE_FAILED:{error_name}",
                event_type="payment",
                actor_type="SYSTEM",
                metadata_json={"reason": str(e), "amount": str(total), "error_class": error_name}
            )
            db.add(audit)
            db.commit()
            raise

    # 4. Create local Order
    order_number = f"ORD-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"
    order = Order(
        merchant_id=merchant_id,
        customer_id=customer_id,
        cart_id=cart_id,
        order_number=order_number,
        status="PENDING",
        subtotal=total + discount,
        discount=discount,
        total=total,
        source=source
    )
    db.add(order)
    db.flush()  # get order.id before using it in audit logs

    # 5. Snapshot items
    for item in cart.items:
        offer = item.offer
        product = offer.product if offer else None

        order_item = OrderItem(
            order_id=order.id,
            offer_id=item.offer_id,
            product_name=product.name if product else "Unknown",
            sku=product.sku if product else "N/A",
            quantity=item.quantity,
            unit_price=offer.price if offer else item.unit_price,
            subtotal=(offer.price if offer else item.unit_price) * item.quantity
        )
        db.add(order_item)

    # Gate-passed audit log WITH order_id now set
    if skip_auth and limits_checked:
        gate_audit = AuditLog(
            merchant_id=merchant_id,
            customer_id=customer_id,
            order_id=order.id,
            action="GATE_PASSED:DIRECT_CHECKOUT",
            event_type="payment",
            actor_type="SYSTEM",
            metadata_json={
                "amount": str(total),
                "limit_checked": limits_checked
            }
        )
        db.add(gate_audit)

    # 6. Create Razorpay Order
    try:
        rp_order = create_rp_order(
            amount_paise=amount_paise,
            currency="INR",
            receipt=str(order.id)
        )
    except RazorpayProviderError as e:
        # Log the provider failure to audit trail with order_id
        audit = AuditLog(
            merchant_id=merchant_id,
            customer_id=customer_id,
            order_id=order.id,
            action="RAZORPAY_PROVIDER_ERROR",
            event_type="payment",
            actor_type="SYSTEM",
            metadata_json={"error": str(e), "order_number": order_number, "amount_paise": amount_paise}
        )
        db.add(audit)
        order.status = "FAILED"
        db.commit()
        raise

    # 7. Create local Payment record
    payment = Payment(
        order_id=order.id,
        provider="razorpay",
        provider_order_id=rp_order["id"],
        amount=total,
        currency="INR",
        status="CREATED"
    )
    db.add(payment)
    db.flush()

    # 8. Audit log — ORDER CREATED — always has order_id
    audit = AuditLog(
        merchant_id=merchant_id,
        customer_id=customer_id,
        order_id=order.id,
        action="PAYMENT_ORDER_CREATED",
        event_type="payment",
        actor_type="SYSTEM",
        metadata_json={
            "razorpay_order_id": rp_order["id"],
            "amount_rupees": str(total),
            "amount_paise": amount_paise,
            "payment_id": str(payment.id),
            "order_number": order_number,
            "agent_trace": agent_trace
        }
    )
    db.add(audit)

    db.commit()

    return {
        "payment_id": str(payment.id),
        "order_id": str(order.id),
        "order_number": order_number,
        "razorpay_order_id": rp_order["id"],
        "razorpay_key_id": RAZORPAY_KEY_ID,
        "amount": amount_paise,
        "amount_rupees": float(total),
        "currency": "INR"
    }


def verify_payment(db: Session, payment_id: str, rp_payment_id: str, rp_order_id: str, rp_signature: str) -> dict:
    payment = db.query(Payment).filter(Payment.id == payment_id).with_for_update().first()
    if not payment:
        raise PaymentStateError("Payment not found")

    order = payment.order

    # Verify signature
    try:
        verify_payment_signature(rp_order_id, rp_payment_id, rp_signature)
    except Exception as e:
        # Use existing db session — no nested Session needed
        audit = AuditLog(
            merchant_id=order.merchant_id,
            customer_id=order.customer_id,
            order_id=order.id,
            action="PAYMENT_VERIFICATION_FAILED",
            event_type="payment",
            actor_type="SYSTEM",
            metadata_json={"error": str(e), "payment_id": str(payment.id)}
        )
        db.add(audit)
        db.commit()
        raise

    # If verification succeeds, update payment status to CAPTURED
    if payment.status != "CAPTURED":
        payment.status = "CAPTURED"
        payment.provider_payment_id = rp_payment_id

        if order.status != "PAID":
            _finalize_order(db, order, payment)

        # Audit for successful capture
        audit = AuditLog(
            merchant_id=order.merchant_id,
            customer_id=order.customer_id,
            order_id=order.id,
            action="PAYMENT_CAPTURED",
            event_type="payment",
            actor_type="SYSTEM",
            metadata_json={
                "razorpay_payment_id": rp_payment_id,
                "razorpay_order_id": rp_order_id,
                "payment_id": str(payment.id),
                "amount_rupees": float(payment.amount)
            }
        )
        db.add(audit)
        db.commit()

    return {
        "status": "success",
        "payment_id": str(payment.id),
        "razorpay_payment_id": rp_payment_id,
        "order_number": order.order_number,
        "amount_rupees": float(payment.amount),
        "captured_at": datetime.utcnow().isoformat(),
        "receipt_url": f"/api/payments/receipt/{str(payment.id)}"
    }


def process_webhook(db: Session, payload: dict):
    """
    Process Razorpay webhook payload.
    """
    event_type = payload.get("event")
    event_id = payload.get("id") or payload.get("event_id")
    account_id = payload.get("account_id")

    # Idempotency check
    existing = db.query(WebhookEvent).filter_by(event_id=event_id).first()
    if existing:
        return {"status": "duplicate"}

    webhook_event = WebhookEvent(
        event_id=event_id,
        event_type=event_type,
        account_id=account_id,
        payload=payload,
        signature_valid=True,
        processed=True,
        processed_at=datetime.utcnow()
    )
    db.add(webhook_event)

    # Process supported events
    if event_type == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        rp_order_id = payment_entity.get("order_id")
        rp_payment_id = payment_entity.get("id")

        if rp_order_id:
            payment = db.query(Payment).filter_by(provider_order_id=rp_order_id).with_for_update().first()
            if payment and payment.status != "CAPTURED":
                payment.status = "CAPTURED"
                payment.provider_payment_id = rp_payment_id
                payment.webhook_verified = True

                order = payment.order
                if order.status != "PAID":
                    _finalize_order(db, order, payment)

                audit = AuditLog(
                    merchant_id=order.merchant_id,
                    customer_id=order.customer_id,
                    order_id=order.id,
                    action="PAYMENT_CAPTURED_WEBHOOK",
                    event_type="payment",
                    actor_type="SYSTEM",
                    metadata_json={
                        "razorpay_payment_id": rp_payment_id,
                        "razorpay_order_id": rp_order_id,
                        "payment_id": str(payment.id),
                        "amount_rupees": float(payment.amount)
                    }
                )
                db.add(audit)

    elif event_type == "payment.failed":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        rp_order_id = payment_entity.get("order_id")
        error_code = payment_entity.get("error_code", "UNKNOWN")
        error_description = payment_entity.get("error_description", "Payment failed")
        error_source = payment_entity.get("error_source", "")
        error_step = payment_entity.get("error_step", "")
        error_reason = payment_entity.get("error_reason", "")

        if rp_order_id:
            payment = db.query(Payment).filter_by(provider_order_id=rp_order_id).with_for_update().first()
            if payment and payment.status not in ["CAPTURED", "REFUNDED"]:
                payment.status = "FAILED"
                payment.webhook_verified = True
                order = payment.order
                order.status = "FAILED"

                audit = AuditLog(
                    merchant_id=order.merchant_id,
                    customer_id=order.customer_id,
                    order_id=order.id,
                    action="PAYMENT_FAILED",
                    event_type="payment",
                    actor_type="SYSTEM",
                    metadata_json={
                        "razorpay_order_id": rp_order_id,
                        "payment_id": str(payment.id),
                        "error_code": error_code,
                        "error_description": error_description,
                        "error_source": error_source,
                        "error_step": error_step,
                        "error_reason": error_reason
                    }
                )
                db.add(audit)

    elif event_type == "refund.created":
        # Stub: surface refund in history without full processing
        refund_entity = payload.get("payload", {}).get("refund", {}).get("entity", {})
        rp_payment_id = refund_entity.get("payment_id")
        refund_amount = refund_entity.get("amount", 0)  # paise

        if rp_payment_id:
            payment = db.query(Payment).filter_by(provider_payment_id=rp_payment_id).first()
            if payment:
                order = payment.order
                audit = AuditLog(
                    merchant_id=order.merchant_id,
                    customer_id=order.customer_id,
                    order_id=order.id,
                    action="REFUND_INITIATED",
                    event_type="refund",
                    actor_type="SYSTEM",
                    metadata_json={
                        "razorpay_payment_id": rp_payment_id,
                        "refund_amount_paise": refund_amount,
                        "refund_amount_rupees": refund_amount / 100,
                        "refund_id": refund_entity.get("id")
                    }
                )
                db.add(audit)

    db.commit()
    return {"status": "processed"}


def charge_headless(
    db: Session,
    payment: Payment,
    razorpay_customer_id: str,
    token_id: str,
    user_email: str,
    user_contact: str = "9999999999"
) -> dict:
    """
    Executes a fully headless S2S agent charge against a saved payment instrument.
    Called from _execute_purchase_stream after a Razorpay order already exists.

    Steps:
      1. Fire createRecurring against (order_id, customer_id, token_id)
      2. Poll up to 10 seconds for status transition from 'created' → 'authorized'/'captured'
      3. Explicitly capture if status is 'authorized'
      4. Write audit log: AGENT_CHARGED_SAVED_INSTRUMENT
      5. Return { razorpay_payment_id, status, receipt_url }

    Raises:
      SavedInstrumentInvalid — token expired/revoked
      ChargeDeclined — issuer decline
      RazorpayProviderError — API failure
    """
    import time
    order = payment.order
    amount_paise = int(payment.amount * 100)

    # Step 1: Fire the S2S recurring charge
    audit_instrument = AuditLog(
        merchant_id=str(order.merchant_id),
        customer_id=str(order.customer_id),
        order_id=order.id,
        action="AGENT_CHARGING_SAVED_INSTRUMENT",
        event_type="payment",
        actor_type="AGENT",
        metadata_json={
            "token_id": token_id,
            "razorpay_customer_id": razorpay_customer_id,
            "razorpay_order_id": payment.provider_order_id,
            "amount_paise": amount_paise,
            "instrument_mode": "headless_s2s"
        }
    )
    db.add(audit_instrument)
    db.flush()

    try:
        rp_pay = charge_saved_instrument(
            order_id=payment.provider_order_id,
            razorpay_customer_id=razorpay_customer_id,
            token_id=token_id,
            amount_paise=amount_paise,
            email=user_email,
            contact=user_contact
        )
    except (SavedInstrumentInvalid, ChargeDeclined, RazorpayProviderError) as e:
        # Log failure
        err_class = type(e).__name__
        audit_fail = AuditLog(
            merchant_id=str(order.merchant_id),
            customer_id=str(order.customer_id),
            order_id=order.id,
            action=f"AGENT_CHARGE_FAILED:{err_class}",
            event_type="payment",
            actor_type="AGENT",
            metadata_json={"reason": str(e), "error_class": err_class}
        )
        db.add(audit_fail)
        order.status = "FAILED"
        payment.status = "FAILED"
        db.commit()
        raise

    rp_payment_id = rp_pay.get("id")
    rp_status = rp_pay.get("status", "created")

    # Step 2: Poll for status (max 10 seconds, 20 attempts × 500ms)
    MAX_POLLS = 20
    for attempt in range(MAX_POLLS):
        if rp_status in ("authorized", "captured"):
            break
        if rp_status in ("failed",):
            audit_declined = AuditLog(
                merchant_id=str(order.merchant_id),
                customer_id=str(order.customer_id),
                order_id=order.id,
                action="AGENT_CHARGE_FAILED:ChargeDeclined",
                event_type="payment",
                actor_type="AGENT",
                metadata_json={"razorpay_payment_id": rp_payment_id, "rp_status": rp_status}
            )
            db.add(audit_declined)
            order.status = "FAILED"
            payment.status = "FAILED"
            db.commit()
            raise ChargeDeclined(f"Recurring charge {rp_payment_id} failed (status: {rp_status})")
        time.sleep(0.5)
        try:
            refreshed = fetch_rp_payment(rp_payment_id)
            rp_status = refreshed.get("status", rp_status)
        except RazorpayProviderError:
            pass  # Keep polling on transient fetch error

    # Step 3: Capture if authorized (not yet auto-captured)
    if rp_status == "authorized":
        try:
            captured = capture_rp_payment(rp_payment_id, amount_paise)
            rp_status = captured.get("status", "captured")
        except RazorpayProviderError as e:
            # Capture failed — log but don't fail the whole flow
            logger.warning(f"Capture failed for {rp_payment_id}: {e}")

    # Step 4: Update local payment record
    payment.provider_payment_id = rp_payment_id
    payment.status = "CAPTURED" if rp_status in ("captured", "authorized") else "CREATED"

    if order.status != "PAID" and payment.status == "CAPTURED":
        _finalize_order(db, order, payment)

    # Step 5: Audit — AGENT_CHARGED_SAVED_INSTRUMENT
    audit_success = AuditLog(
        merchant_id=str(order.merchant_id),
        customer_id=str(order.customer_id),
        order_id=order.id,
        action="AGENT_CHARGED_SAVED_INSTRUMENT",
        event_type="payment",
        actor_type="AGENT",
        metadata_json={
            "razorpay_payment_id": rp_payment_id,
            "razorpay_order_id": payment.provider_order_id,
            "token_id": token_id,
            "razorpay_customer_id": razorpay_customer_id,
            "instrument_mode": "headless_s2s",
            "final_status": rp_status,
            "amount_rupees": float(payment.amount),
            "note": "Agent charged pre-authorized saved instrument — no human card entry required"
        }
    )
    db.add(audit_success)
    db.commit()

    return {
        "status": "success",
        "payment_mode": "headless_s2s",
        "razorpay_payment_id": rp_payment_id,
        "razorpay_order_id": payment.provider_order_id,
        "order_number": order.order_number,
        "amount_rupees": float(payment.amount),
        "captured_at": datetime.utcnow().isoformat(),
        "receipt_url": f"/api/payments/receipt/{str(payment.id)}",
        "payment_id": str(payment.id),
    }


def _finalize_order(db: Session, order: Order, payment: Payment):
    """
    Internal function to decrement inventory and mark order paid.
    Assumes within a transaction. Uses the SAME db session — no nested sessions.
    """
    # 1. Check amount mismatch
    expected_amount = order.total
    if payment.amount != expected_amount:
        audit = AuditLog(
            merchant_id=order.merchant_id,
            customer_id=order.customer_id,
            order_id=order.id,
            action="PAYMENT_AMOUNT_MISMATCH",
            event_type="payment",
            actor_type="SYSTEM",
            metadata_json={
                "expected": str(expected_amount),
                "actual": str(payment.amount),
                "payment_id": str(payment.id)
            }
        )
        db.add(audit)
        raise AmountMismatchError("Payment amount does not match order total")

    # 2. Decrement inventory atomically
    from sqlalchemy import text
    from app.models.agent import AgentDecision
    for item in order.items:
        result = db.execute(text("""
            UPDATE inventories
            SET quantity = quantity - :qty
            WHERE offer_id = :offer_id AND quantity >= :qty
        """), {"qty": item.quantity, "offer_id": item.offer_id})
        if result.rowcount == 0:
            decision = AgentDecision(
                customer_id=order.customer_id,
                merchant_id=order.merchant_id,
                action="PAYMENT_FINALIZATION",
                actor_type="SYSTEM",
                decision_status="REJECTED",
                policy_rules=["insufficient_stock"]
            )
            db.add(decision)
            raise PaymentStateError(f"Insufficient inventory for offer {item.offer_id}")

    # 3. Mark paid and cart COMPLETED
    order.status = "PAID"
    if order.cart_id:
        cart = db.query(Cart).filter_by(id=order.cart_id).first()
        if cart:
            cart.status = "COMPLETED"

    # 4. Audit
    audit = AuditLog(
        merchant_id=order.merchant_id,
        customer_id=order.customer_id,
        order_id=order.id,
        action="ORDER_PAID",
        event_type="order",
        actor_type="SYSTEM",
        metadata_json={
            "order_number": order.order_number,
            "source": order.source,
            "order_id": str(order.id)
        }
    )
    db.add(audit)

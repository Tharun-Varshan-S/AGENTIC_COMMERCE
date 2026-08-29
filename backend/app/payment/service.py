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
from app.payment.razorpay_client import create_order as create_rp_order, verify_payment_signature, RAZORPAY_KEY_ID
from app.payment.exceptions import PaymentStateError, AmountMismatchError

from app.payment.schemas import DirectCheckoutRequest

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
        return create_payment_order(
            db=db,
            merchant_id=req.merchant_id,
            customer_id=req.customer_id,
            cart_id=str(cart.id),
            source=req.source,
            agent_trace=req.agent_trace,
            human_approval=req.human_approval
        )
    except Exception as e:
        if isinstance(e, PaymentStateError):
            raise e
        raise PaymentStateError(f"Direct checkout failed: {str(e)}")

def create_payment_order(db: Session, merchant_id: str, customer_id: str, cart_id: str, source: str = "DIRECT", agent_trace: dict = None, human_approval: bool = False) -> dict:
    # 1. Load the cart
    cart = db.query(Cart).filter(
        Cart.id == cart_id,
        Cart.customer_id == customer_id,
        Cart.merchant_id == merchant_id,
        Cart.status == "ACTIVE"
    ).first()
    if not cart:
        raise PaymentStateError("Cart not found or not active")

    # 2. Policy Engine (which also checks inventory and recalculates price)
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
        # Check if consent is already approved
        # For this MVP, we assume consent check is enforced before this point if REQUIRES_CONSENT,
        # but to be safe we can query ConsentRequest
        from app.models.consent import ConsentRequest
        consent = db.query(ConsentRequest).filter(
            ConsentRequest.cart_id == cart_id,
            ConsentRequest.status == "APPROVED"
        ).first()
        if not consent:
            raise PaymentStateError("Consent required but not approved")

    # 3. Calculate authoritative amount
    # Instead of trusting cart.total, we recalculate or trust the engine's recalculation.
    # The policy engine ensures prices are valid. We will just sum cart items safely.
    total = sum((item.offer.price * item.quantity) for item in cart.items if item.offer)
    discount = cart.discount or Decimal('0')
    total -= discount
    if total <= 0:
        raise PaymentStateError("Invalid cart total")
        
    amount_paise = int(total * 100)

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
    db.flush()

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
            unit_price=item.unit_price,
            subtotal=item.unit_price * item.quantity
        )
        db.add(order_item)

    # 6. Create Razorpay Order
    rp_order = create_rp_order(
        amount_paise=amount_paise,
        currency="INR",
        receipt=str(order.id)
    )

    # 7. Create local Payment
    payment = Payment(
        order_id=order.id,
        provider="razorpay",
        provider_order_id=rp_order["id"],
        amount=total,
        currency="INR",
        status="CREATED"
    )
    db.add(payment)

    # 9. Audit log
    audit = AuditLog(
        merchant_id=merchant_id,
        customer_id=customer_id,
        action="PAYMENT_ORDER_CREATED",
        event_type="payment",
        actor_type="SYSTEM",
        metadata_json={"razorpay_order_id": rp_order["id"], "amount": str(total), "payment_id": str(payment.id), "agent_trace": agent_trace}
    )
    db.add(audit)
    
    db.commit()

    return {
        "payment_id": payment.id,
        "razorpay_order_id": rp_order["id"],
        "razorpay_key_id": RAZORPAY_KEY_ID,
        "amount": amount_paise,
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
        audit = AuditLog(
            merchant_id=order.merchant_id,
            customer_id=order.customer_id,
            action="PAYMENT_VERIFICATION_FAILED",
            event_type="payment",
            actor_type="SYSTEM",
            metadata_json={"error": str(e), "payment_id": str(payment.id)}
        )
        db.add(audit)
        db.commit()
        raise

    # If verification succeeds, update payment status to CAPTURED and order to PAID
    # This might also happen via webhook, so we check if already CAPTURED
    if payment.status != "CAPTURED":
        payment.status = "CAPTURED"
        payment.provider_payment_id = rp_payment_id
        
        # We only finalize the order if it wasn't already (e.g. by webhook)
        if order.status != "PAID":
            _finalize_order(db, order, payment)

        db.commit()

    return {"status": "success", "payment_id": payment.id, "order_number": order.order_number}

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
                
                order = payment.order
                if order.status != "PAID":
                    _finalize_order(db, order, payment)
                    
    elif event_type == "payment.failed":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        rp_order_id = payment_entity.get("order_id")
        
        if rp_order_id:
            payment = db.query(Payment).filter_by(provider_order_id=rp_order_id).with_for_update().first()
            if payment and payment.status not in ["CAPTURED", "REFUNDED"]:
                payment.status = "FAILED"
                order = payment.order
                order.status = "FAILED"
                
                audit = AuditLog(
                    merchant_id=order.merchant_id,
                    customer_id=order.customer_id,
                    action="PAYMENT_FAILED",
                    event_type="payment",
                    actor_type="SYSTEM",
                    metadata_json={"razorpay_order_id": rp_order_id, "payment_id": str(payment.id)}
                )
                db.add(audit)
                
    db.commit()
    return {"status": "processed"}

def _finalize_order(db: Session, order: Order, payment: Payment):
    """
    Internal function to decrement inventory and mark order paid.
    Assumes within a transaction.
    """
    # 1. Check amount mismatch
    expected_amount = order.total
    if payment.amount != expected_amount:
        audit = AuditLog(
            merchant_id=order.merchant_id,
            customer_id=order.customer_id,
            action="PAYMENT_AMOUNT_MISMATCH",
            event_type="payment",
            actor_type="SYSTEM",
            metadata_json={"expected": str(expected_amount), "actual": str(payment.amount), "payment_id": str(payment.id)}
        )
        db.add(audit)
        raise AmountMismatchError("Payment amount does not match order total")
        
    # 2. Decrement inventory
    from app.models.product import Inventory
    for item in order.items:
        inv = db.query(Inventory).filter_by(offer_id=item.offer_id).with_for_update().first()
        if not inv or inv.quantity < item.quantity:
            # We fail finalization if oversold
            raise PaymentStateError(f"Insufficient inventory for offer {item.offer_id}")
        inv.quantity -= item.quantity
        
    # 3. Mark paid and cart COMPLETED
    order.status = "PAID"
    if order.cart_id:
        cart = db.query(Cart).filter_by(id=order.cart_id).first()
        if cart:
            cart.status = "COMPLETED"
    
    # 4. Audit
    audit1 = AuditLog(
        merchant_id=order.merchant_id,
        customer_id=order.customer_id,
        action="ORDER_PAID",
        event_type="order",
        actor_type="SYSTEM",
        metadata_json={"order_number": order.order_number, "source": order.source, "order_id": str(order.id)}
    )
    db.add(audit1)

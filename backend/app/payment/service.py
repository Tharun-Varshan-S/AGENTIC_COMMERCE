import uuid
from decimal import Decimal
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.order import Cart, Order, OrderItem, Payment, WebhookEvent
from app.models.audit import AuditLog
from app.policy.service import PolicyService
from app.policy.schemas import PolicyEvaluationRequest
from app.payment.razorpay_client import create_order as create_rp_order, verify_payment_signature, RAZORPAY_KEY_ID
from app.payment.exceptions import PaymentStateError, AmountMismatchError

def create_payment_order(db: Session, merchant_id: str, customer_id: str, cart_id: str, source: str = "DIRECT", agent_trace: dict = None) -> dict:
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
    total = sum((item.unit_price * item.quantity) for item in cart.items)
    total -= cart.discount
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
        subtotal=total + cart.discount,
        discount=cart.discount,
        total=total,
        source=source,
        metadata_json={"agent_trace": agent_trace} if agent_trace else {}
    )
    db.add(order)
    db.flush()

    # 5. Snapshot items
    for item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            product_name=item.product.name,
            sku=item.product.sku,
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.unit_price * item.quantity
        )
        db.add(order_item)

    # 6. Create Razorpay Order
    rp_order = create_rp_order(
        amount_paise=amount_paise,
        currency="INR",
        receipt=order.id
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

    # 8. Mark cart as CHECKOUT
    cart.status = "CHECKOUT"

    # 9. Audit log
    audit = AuditLog(
        merchant_id=merchant_id,
        customer_id=customer_id,
        action="PAYMENT_ORDER_CREATED",
        entity_type="payment",
        entity_id=payment.id,
        details={"razorpay_order_id": rp_order["id"], "amount": str(total)}
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
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
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
            entity_type="payment",
            entity_id=payment.id,
            details={"error": str(e)}
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
    
    # Idempotency check
    existing = db.query(WebhookEvent).filter_by(provider="razorpay", provider_event_id=event_id).first()
    if existing:
        return {"status": "duplicate"}
        
    webhook_event = WebhookEvent(
        provider="razorpay",
        provider_event_id=event_id,
        event_type=event_type,
        processed="PROCESSED"
    )
    db.add(webhook_event)
    
    # Process supported events
    if event_type == "payment.captured":
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        rp_order_id = payment_entity.get("order_id")
        rp_payment_id = payment_entity.get("id")
        
        if rp_order_id:
            payment = db.query(Payment).filter_by(provider_order_id=rp_order_id).first()
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
            payment = db.query(Payment).filter_by(provider_order_id=rp_order_id).first()
            if payment and payment.status not in ["CAPTURED", "REFUNDED"]:
                payment.status = "FAILED"
                order = payment.order
                order.status = "FAILED"
                
                audit = AuditLog(
                    merchant_id=order.merchant_id,
                    customer_id=order.customer_id,
                    action="PAYMENT_FAILED",
                    entity_type="payment",
                    entity_id=payment.id,
                    details={"razorpay_order_id": rp_order_id}
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
            entity_type="payment",
            entity_id=payment.id,
            details={"expected": str(expected_amount), "actual": str(payment.amount)}
        )
        db.add(audit)
        raise AmountMismatchError("Payment amount does not match order total")
        
    # 2. Decrement inventory
    from app.models.product import Inventory
    for item in order.items:
        inv = db.query(Inventory).filter_by(product_id=item.product_id).with_for_update().first()
        if not inv or inv.quantity < item.quantity:
            # We fail finalization if oversold
            raise PaymentStateError(f"Insufficient inventory for product {item.product_id}")
        inv.quantity -= item.quantity
        
    # 3. Mark paid
    order.status = "PAID"
    
    # 4. Audit
    audit1 = AuditLog(
        merchant_id=order.merchant_id,
        customer_id=order.customer_id,
        action="ORDER_PAID",
        entity_type="order",
        entity_id=order.id,
        details={"order_number": order.order_number, "source": order.source}
    )
    db.add(audit1)

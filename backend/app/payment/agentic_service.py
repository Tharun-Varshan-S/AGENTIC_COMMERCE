import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.payment_authorization import AgenticPaymentAuthorization
from app.models.order import Order, Payment, Cart
from app.models.audit import AuditLog
from app.payment.exceptions import PaymentStateError
from app.payment.razorpay_client import create_order as create_rp_order

def setup_agentic_authorization(db: Session, customer_id: str, per_transaction_limit: Decimal, daily_limit: Decimal) -> AgenticPaymentAuthorization:
    # Check if active one exists and revoke it
    existing = db.query(AgenticPaymentAuthorization).filter(
        AgenticPaymentAuthorization.customer_id == customer_id,
        AgenticPaymentAuthorization.status == "ACTIVE"
    ).all()
    for auth in existing:
        auth.status = "REVOKED"

    auth = AgenticPaymentAuthorization(
        customer_id=customer_id,
        provider="razorpay",
        rail="upi_reserve_pay",
        authorization_reference=f"auth_{uuid.uuid4().hex[:10]}", # Mocking Razorpay authorization ID
        status="ACTIVE",
        per_transaction_limit=per_transaction_limit,
        daily_limit=daily_limit,
        spent_today=Decimal('0'),
        expires_at=datetime.utcnow() + timedelta(days=30)
    )
    db.add(auth)
    db.commit()
    db.refresh(auth)
    return auth

def get_active_authorization(db: Session, customer_id: str) -> AgenticPaymentAuthorization | None:
    return db.query(AgenticPaymentAuthorization).filter(
        AgenticPaymentAuthorization.customer_id == customer_id,
        AgenticPaymentAuthorization.status == "ACTIVE",
        # Check expiry
    ).first()

def revoke_authorization(db: Session, auth_id: str) -> bool:
    auth = db.query(AgenticPaymentAuthorization).filter(AgenticPaymentAuthorization.id == auth_id).first()
    if auth:
        auth.status = "REVOKED"
        db.commit()
        return True
    return False

def execute_agentic_payment(db: Session, merchant_id: str, customer_id: str, cart_id: str) -> dict:
    """
    Executes a payment completely on the backend utilizing the agentic authorization.
    This simulates the call to the Razorpay Agentic Payments execution API.
    """
    auth = get_active_authorization(db, customer_id)
    if not auth:
        raise PaymentStateError("No active agentic payment authorization found.")

    if auth.expires_at and auth.expires_at < datetime.utcnow():
        auth.status = "EXPIRED"
        db.commit()
        raise PaymentStateError("Agentic payment authorization expired.")

    cart = db.query(Cart).filter(
        Cart.id == cart_id,
        Cart.customer_id == customer_id,
        Cart.merchant_id == merchant_id,
        Cart.status == "ACTIVE"
    ).first()
    if not cart:
        raise PaymentStateError("Cart not found or not active")

    total = sum((item.unit_price * item.quantity) for item in cart.items)
    discount = cart.discount or Decimal('0')
    total -= discount
    if total <= 0:
        raise PaymentStateError("Invalid cart total")

    # Policy limit enforcement is strictly done here or earlier. We do it here as well for safety.
    if total > auth.per_transaction_limit:
        raise PaymentStateError(f"Amount {total} exceeds per transaction limit of {auth.per_transaction_limit}")
    
    # Simple daily check (in production, reset logic needs to be robust)
    if auth.spent_today + total > auth.daily_limit:
        raise PaymentStateError(f"Amount {total} exceeds remaining daily limit")

    # 1. Create order
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
        source="AGENTIC"
    )
    db.add(order)
    db.flush()

    # Move items
    from app.models.order import OrderItem
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

    # 2. Call Razorpay (Simulation of Agentic Payment API)
    # Since UPI Reserve Pay execution API may be private/beta, we mock the success response.
    rp_payment_id = f"pay_{uuid.uuid4().hex[:14]}"
    
    # Create Payment Record
    payment = Payment(
        order_id=order.id,
        provider="razorpay",
        provider_order_id=f"agentic_ord_{uuid.uuid4().hex[:10]}",
        provider_payment_id=rp_payment_id,
        amount=total,
        currency="INR",
        status="CAPTURED", # Marking as captured immediately as agentic execution is synchronous
        agentic_authorization_id=auth.id
    )
    db.add(payment)

    # Update Auth Spending
    auth.spent_today += total

    # Finalize
    order.status = "PAID"
    cart.status = "COMPLETED"

    # Decrement inventory
    from app.models.product import Inventory
    for item in order.items:
        inv = db.query(Inventory).filter_by(offer_id=item.offer_id).with_for_update().first()
        if inv and inv.quantity >= item.quantity:
            inv.quantity -= item.quantity

    audit = AuditLog(
        merchant_id=merchant_id,
        customer_id=customer_id,
        action="AGENTIC_PAYMENT_EXECUTED",
        event_type="payment",
        actor_type="SYSTEM",
        metadata_json={
            "auth_id": str(auth.id),
            "amount": str(total),
            "payment_id": str(payment.id),
            "order_number": order.order_number
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "success",
        "payment_id": str(payment.id),
        "order_number": order.order_number,
        "amount": str(total),
        "message": "Payment executed via agentic capability"
    }

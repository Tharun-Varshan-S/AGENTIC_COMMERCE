import uuid
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.payment_authorization import AgenticPaymentAuthorization
from app.models.order import Order, Payment, Cart, CartItem
from app.models.audit import AuditLog
from app.payment.exceptions import PaymentStateError
from app.payment.razorpay_client import create_order as create_rp_order
from app.models.offer import Offer

def setup_agentic_authorization(db: Session, merchant_id: str, customer_id: str, per_transaction_limit: Decimal, daily_limit: Decimal) -> AgenticPaymentAuthorization:
    # Check if active one exists and revoke it
    existing = db.query(AgenticPaymentAuthorization).filter(
        AgenticPaymentAuthorization.customer_id == customer_id,
        AgenticPaymentAuthorization.status == "ACTIVE"
    ).all()
    for auth in existing:
        auth.status = "REVOKED"

    auth = AgenticPaymentAuthorization(
        customer_id=customer_id,
        merchant_id=merchant_id,
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
        AgenticPaymentAuthorization.expires_at > datetime.utcnow()
    ).first()

def revoke_authorization(db: Session, auth_id: str, actor_type: str = "CUSTOMER") -> bool:
    auth = db.query(AgenticPaymentAuthorization).filter(AgenticPaymentAuthorization.id == auth_id).first()
    if auth:
        auth.status = "REVOKED"
        
        audit = AuditLog(
            merchant_id=auth.merchant_id,
            customer_id=auth.customer_id,
            action="AGENTIC_AUTHORIZATION_REVOKED",
            event_type="security",
            actor_type=actor_type,
            metadata_json={
                "auth_id": str(auth.id)
            }
        )
        db.add(audit)
        
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

    if str(auth.merchant_id) != str(merchant_id):
        from app.models.agent import AgentDecision
        with Session(db.get_bind()) as audit_db:
            decision = AgentDecision(
                customer_id=customer_id,
                merchant_id=merchant_id,
                action="AGENTIC_PAYMENT_EXECUTION",
                actor_type="SYSTEM",
                decision_status="REJECTED",
                policy_rules=["authorization_merchant_mismatch"]
            )
            audit_db.add(decision)
            audit_db.commit()
        raise PaymentStateError("authorization_merchant_mismatch")

    if auth.expires_at and auth.expires_at.replace(tzinfo=None) < datetime.utcnow():
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

    total = sum((item.offer.price * item.quantity) for item in cart.items if item.offer)
    discount = cart.discount or Decimal('0')
    total -= discount
    if total <= 0:
        raise PaymentStateError("Invalid cart total")

    # Policy limit enforcement is strictly done here or earlier. We do it here as well for safety.
    if total > auth.per_transaction_limit:
        raise PaymentStateError(f"Amount {total} exceeds per transaction limit of {auth.per_transaction_limit}")
    
    # Atomic daily check and increment
    from sqlalchemy import text
    from app.models.agent import AgentDecision
    result = db.execute(text("""
        UPDATE agentic_payment_authorizations 
        SET spent_today = spent_today + :total 
        WHERE id = :id AND spent_today + :total <= daily_limit
    """), {"total": total, "id": auth.id})
    if result.rowcount == 0:
        with Session(db.get_bind()) as audit_db:
            decision = AgentDecision(
                customer_id=customer_id,
                merchant_id=merchant_id,
                action="AGENTIC_PAYMENT_EXECUTION",
                actor_type="SYSTEM",
                decision_status="REJECTED",
                policy_rules=["daily_limit_exceeded"]
            )
            audit_db.add(decision)
            audit_db.commit()
        raise PaymentStateError(f"Amount {total} exceeds remaining daily limit")

    # 1. Create or retrieve order for cart
    existing_order = db.query(Order).filter(Order.cart_id == cart_id).first()
    if existing_order:
        if existing_order.status == "PAID":
            cart.status = "COMPLETED"
            db.commit()
            payment_id = str(existing_order.payment.id) if existing_order.payment else "N/A"
            return {
                "status": "success",
                "payment_id": payment_id,
                "order_number": existing_order.order_number,
                "amount": str(existing_order.total),
                "message": "Payment already completed for this cart"
            }
        order = existing_order
        order.status = "PENDING"
        order.source = "AGENTIC"
    else:
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

    # Move items if order items not present
    if not order.items:
        from app.models.order import OrderItem
        for item in cart.items:
            offer = item.offer
            if not offer:
                continue
            product = offer.product if offer else None
            order_item = OrderItem(
                order_id=order.id,
                offer_id=item.offer_id,
                product_name=product.name if product else "Unknown",
                sku=product.sku if product else "N/A",
                quantity=item.quantity,
                unit_price=offer.price,
                subtotal=offer.price * item.quantity
            )
            db.add(order_item)

    # 2. Call Razorpay
    amount_paise = int(total * 100)
    rp_order = create_rp_order(
        amount_paise=amount_paise,
        currency="INR",
        receipt=str(order.id)
    )
    
    # Create Payment Record
    payment = Payment(
        order_id=order.id,
        provider="razorpay",
        provider_order_id=rp_order["id"],
        provider_payment_id=f"pay_agentic_{uuid.uuid4().hex[:10]}",
        amount=total,
        currency="INR",
        status="PAID",
        agentic_authorization_id=auth.id
    )
    db.add(payment)

    # Auth spending already updated atomically earlier

    # Finalize
    order.status = "PAID"

    # Decrement inventory atomically
    for item in cart.items:
        if not item.offer_id:
            continue
        result = db.execute(text("""
            UPDATE inventories 
            SET quantity = quantity - :qty 
            WHERE offer_id = :offer_id AND quantity >= :qty
        """), {"qty": item.quantity, "offer_id": item.offer_id})
        if result.rowcount == 0:
            with Session(db.get_bind()) as audit_db:
                decision = AgentDecision(
                    customer_id=customer_id,
                    merchant_id=merchant_id,
                    action="AGENTIC_PAYMENT_EXECUTION",
                    actor_type="SYSTEM",
                    decision_status="REJECTED",
                    policy_rules=["insufficient_stock"]
                )
                audit_db.add(decision)
                audit_db.commit()
            raise PaymentStateError(f"Insufficient inventory for offer {item.offer_id}")

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

def execute_direct_agentic_payment(db: Session, merchant_id: str, customer_id: str, offer_id: str, quantity: int) -> dict:
    """
    Executes a direct (single-product) payment completely on the backend utilizing the agentic authorization.
    """
    auth = get_active_authorization(db, customer_id)
    if not auth:
        raise PaymentStateError("No active agentic payment authorization found.")

    if str(auth.merchant_id) != str(merchant_id):
        from app.models.agent import AgentDecision
        with Session(db.get_bind()) as audit_db:
            decision = AgentDecision(
                customer_id=customer_id,
                merchant_id=merchant_id,
                action="AGENTIC_PAYMENT_EXECUTION",
                actor_type="SYSTEM",
                decision_status="REJECTED",
                policy_rules=["authorization_merchant_mismatch"]
            )
            audit_db.add(decision)
            audit_db.commit()
        raise PaymentStateError("authorization_merchant_mismatch")

    if auth.expires_at and auth.expires_at.replace(tzinfo=None) < datetime.utcnow():
        auth.status = "EXPIRED"
        db.commit()
        raise PaymentStateError("Agentic payment authorization expired.")

    offer = db.query(Offer).filter(Offer.id == offer_id, Offer.merchant_id == merchant_id).first()
    if not offer:
        raise PaymentStateError("Offer not found")

    total = offer.price * quantity
    if total <= 0:
        raise PaymentStateError("Invalid total amount")

    if total > auth.per_transaction_limit:
        raise PaymentStateError(f"Amount {total} exceeds per transaction limit of {auth.per_transaction_limit}")
    
    from sqlalchemy import text
    from app.models.agent import AgentDecision
    result = db.execute(text("""
        UPDATE agentic_payment_authorizations 
        SET spent_today = spent_today + :total 
        WHERE id = :id AND spent_today + :total <= daily_limit
    """), {"total": total, "id": auth.id})
    if result.rowcount == 0:
        with Session(db.get_bind()) as audit_db:
            decision = AgentDecision(
                customer_id=customer_id,
                merchant_id=merchant_id,
                action="AGENTIC_PAYMENT_EXECUTION",
                actor_type="SYSTEM",
                decision_status="REJECTED",
                policy_rules=["daily_limit_exceeded"]
            )
            audit_db.add(decision)
            audit_db.commit()
        raise PaymentStateError(f"Amount {total} exceeds remaining daily limit")

    # Create ephemeral Cart for direct agentic payment
    cart = Cart(
        customer_id=customer_id,
        merchant_id=merchant_id,
        status="COMPLETED",
        currency="INR",
        discount=Decimal('0')
    )
    db.add(cart)
    db.flush()

    cart_item = CartItem(
        cart_id=cart.id,
        offer_id=offer.id,
        quantity=quantity,
        unit_price=offer.price
    )
    db.add(cart_item)
    db.flush()

    order_number = f"ORD-{datetime.utcnow().year}-{uuid.uuid4().hex[:6].upper()}"
    order = Order(
        merchant_id=merchant_id,
        customer_id=customer_id,
        cart_id=cart.id,
        order_number=order_number,
        status="PAID",
        subtotal=total,
        discount=Decimal('0'),
        total=total,
        source="AGENTIC"
    )
    db.add(order)
    db.flush()

    product = offer.product
    from app.models.order import OrderItem
    order_item = OrderItem(
        order_id=order.id,
        offer_id=offer.id,
        product_name=product.name if product else "Unknown",
        sku=product.sku if product else "N/A",
        quantity=quantity,
        unit_price=offer.price,
        subtotal=total
    )
    db.add(order_item)

    amount_paise = int(total * 100)
    rp_order = create_rp_order(
        amount_paise=amount_paise,
        currency="INR",
        receipt=str(order.id)
    )
    
    payment = Payment(
        order_id=order.id,
        provider="razorpay",
        provider_order_id=rp_order["id"],
        provider_payment_id=f"pay_agentic_{uuid.uuid4().hex[:10]}",
        amount=total,
        currency="INR",
        status="PAID",
        agentic_authorization_id=auth.id
    )
    db.add(payment)

    result = db.execute(text("""
        UPDATE inventories 
        SET quantity = quantity - :qty 
        WHERE offer_id = :offer_id AND quantity >= :qty
    """), {"qty": quantity, "offer_id": offer.id})
    
    if result.rowcount == 0:
        with Session(db.get_bind()) as audit_db:
            decision = AgentDecision(
                customer_id=customer_id,
                merchant_id=merchant_id,
                action="AGENTIC_PAYMENT_EXECUTION",
                actor_type="SYSTEM",
                decision_status="REJECTED",
                policy_rules=["insufficient_stock"]
            )
            audit_db.add(decision)
            audit_db.commit()
        raise PaymentStateError(f"Insufficient inventory for offer {offer.id}")

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

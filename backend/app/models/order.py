from sqlalchemy import Column, String, Numeric, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class Cart(BaseModel):
    __tablename__ = "carts"

    customer_id = Column(ForeignKey("customers.id"), nullable=False, index=True)
    merchant_id = Column(ForeignKey("merchants.id"), nullable=False, index=True)
    status = Column(String, default="ACTIVE", nullable=False) # ACTIVE, CHECKOUT, COMPLETED, ABANDONED
    currency = Column(String, default="INR", nullable=False)
    discount = Column(Numeric(10, 2), default=0)

    customer = relationship("Customer", back_populates="carts")
    merchant = relationship("Merchant", viewonly=True) # Merchant relationship mostly via customer, but keep a link
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    order = relationship("Order", back_populates="cart", uselist=False)

class CartItem(BaseModel):
    __tablename__ = "cart_items"

    cart_id = Column(ForeignKey("carts.id"), nullable=False, index=True)
    offer_id = Column(ForeignKey("offers.id"), nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)

    cart = relationship("Cart", back_populates="items")
    offer = relationship("Offer", back_populates="cart_items")

class Order(BaseModel):
    __tablename__ = "orders"

    merchant_id = Column(ForeignKey("merchants.id"), nullable=False, index=True)
    customer_id = Column(ForeignKey("customers.id"), nullable=False, index=True)
    cart_id = Column(ForeignKey("carts.id"), nullable=False, unique=True, index=True)
    order_number = Column(String, nullable=False, unique=True, index=True)
    status = Column(String, default="PENDING", nullable=False) # PENDING, CONFIRMED, PAID, CANCELLED, FAILED
    source = Column(String, default="DIRECT", nullable=False) # DIRECT, AI
    currency = Column(String, default="INR", nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)
    discount = Column(Numeric(10, 2), default=0)
    total = Column(Numeric(10, 2), nullable=False)

    merchant = relationship("Merchant", back_populates="orders")
    customer = relationship("Customer", back_populates="orders")
    cart = relationship("Cart", back_populates="order")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="order", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="order", cascade="all, delete-orphan")

class OrderItem(BaseModel):
    __tablename__ = "order_items"

    order_id = Column(ForeignKey("orders.id"), nullable=False, index=True)
    offer_id = Column(ForeignKey("offers.id"), nullable=False, index=True)
    product_name = Column(String, nullable=False)
    sku = Column(String, nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(Numeric(10, 2), nullable=False)

    order = relationship("Order", back_populates="items")
    offer = relationship("Offer", back_populates="order_items")

class Payment(BaseModel):
    __tablename__ = "payments"

    order_id = Column(ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    provider = Column(String, nullable=False)
    provider_order_id = Column(String)
    provider_payment_id = Column(String)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="INR", nullable=False)
    status = Column(String, default="CREATED", nullable=False) # CREATED, AUTHORIZED, CAPTURED, FAILED, REFUNDED

    order = relationship("Order", back_populates="payment")

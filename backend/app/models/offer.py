from sqlalchemy import Column, String, Boolean, Numeric, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class Offer(BaseModel):
    __tablename__ = "offers"

    product_id = Column(ForeignKey("products.id"), nullable=False, index=True)
    merchant_id = Column(ForeignKey("merchants.id"), nullable=False, index=True)
    price = Column(Numeric(10, 2), nullable=False)
    mrp = Column(Numeric(10, 2))
    currency = Column(String, default="INR", nullable=False)
    delivery_estimate = Column(String)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_sponsored = Column(Boolean, default=False)
    source = Column(String, default="razorpay", nullable=False) # e.g. "razorpay", "amazon", "flipkart"

    product = relationship("Product", back_populates="offers")
    merchant = relationship("Merchant", back_populates="offers")
    inventory = relationship("Inventory", back_populates="offer", uselist=False, cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="offer", cascade="all, delete-orphan")
    order_items = relationship("OrderItem", back_populates="offer", cascade="all, delete-orphan")

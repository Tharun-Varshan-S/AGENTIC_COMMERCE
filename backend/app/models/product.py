from sqlalchemy import Column, String, Boolean, Numeric, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class Product(BaseModel):
    __tablename__ = "products"

    merchant_id = Column(ForeignKey("merchants.id"), nullable=False, index=True)
    sku = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    category = Column(String, index=True)
    brand = Column(String)
    price = Column(Numeric(10, 2), nullable=False)
    cost_price = Column(Numeric(10, 2))
    currency = Column(String, default="INR", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    source = Column(String, default="razorpay", nullable=False, index=True)
    rating = Column(Numeric(3, 2))
    review_count = Column(Integer, default=0)
    delivery_estimate = Column(String)
    is_sponsored = Column(Boolean, default=False)
    product_url = Column(String)
    image_url = Column(String)
    mrp = Column(Numeric(10, 2))
    metadata_json = Column("metadata", JSONB) # Renamed attribute slightly to avoid Python issues, but column is metadata

    merchant = relationship("Merchant", back_populates="products")
    inventory = relationship("Inventory", back_populates="product", uselist=False, cascade="all, delete-orphan")
    customer_events = relationship("CustomerEvent", back_populates="product", cascade="all, delete-orphan")
    cart_items = relationship("CartItem", back_populates="product", cascade="all, delete-orphan")
    agent_decisions_primary = relationship("AgentDecision", foreign_keys="[AgentDecision.primary_product_id]", back_populates="primary_product")
    agent_decisions_recommended = relationship("AgentDecision", foreign_keys="[AgentDecision.recommended_product_id]", back_populates="recommended_product")
    promotions = relationship("Promotion", back_populates="product", cascade="all, delete-orphan")


class Inventory(BaseModel):
    __tablename__ = "inventories"

    product_id = Column(ForeignKey("products.id"), nullable=False, unique=True, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    reorder_level = Column(Integer, default=0)

    product = relationship("Product", back_populates="inventory")

from sqlalchemy import Column, String, Boolean, Numeric, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class Product(BaseModel):
    __tablename__ = "products"

    merchant_id = Column(ForeignKey("merchants.id"), nullable=True, index=True) # Optional original manufacturer/brand merchant link
    sku = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    category = Column(String, index=True)
    brand = Column(String)
    rating = Column(Numeric(3, 2))
    review_count = Column(Integer, default=0)
    product_url = Column(String)
    image_url = Column(String)
    metadata_json = Column("metadata", JSONB)

    merchant = relationship("Merchant", back_populates="products")
    offers = relationship("Offer", back_populates="product", cascade="all, delete-orphan")
    customer_events = relationship("CustomerEvent", back_populates="product", cascade="all, delete-orphan")
    agent_decisions_primary = relationship("AgentDecision", foreign_keys="[AgentDecision.primary_product_id]", back_populates="primary_product")
    agent_decisions_recommended = relationship("AgentDecision", foreign_keys="[AgentDecision.recommended_product_id]", back_populates="recommended_product")
    promotions = relationship("Promotion", back_populates="product", cascade="all, delete-orphan")


class Inventory(BaseModel):
    __tablename__ = "inventories"

    offer_id = Column(ForeignKey("offers.id"), nullable=False, unique=True, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    reserved_quantity = Column(Integer, default=0, nullable=False)
    reorder_level = Column(Integer, default=0)

    offer = relationship("Offer", back_populates="inventory")

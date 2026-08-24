from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class Customer(BaseModel):
    __tablename__ = "customers"

    merchant_id = Column(ForeignKey("merchants.id"), nullable=False, index=True)
    external_reference = Column(String)
    name = Column(String, nullable=False)
    email = Column(String)
    budget_preference = Column(String)

    merchant = relationship("Merchant", back_populates="customers")
    events = relationship("CustomerEvent", back_populates="customer", cascade="all, delete-orphan")
    carts = relationship("Cart", back_populates="customer", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    agent_decisions = relationship("AgentDecision", back_populates="customer", cascade="all, delete-orphan")

class CustomerEvent(BaseModel):
    __tablename__ = "customer_events"

    customer_id = Column(ForeignKey("customers.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    product_id = Column(ForeignKey("products.id"), nullable=True, index=True)
    metadata_json = Column("metadata", JSONB)

    customer = relationship("Customer", back_populates="events")
    product = relationship("Product", back_populates="customer_events")

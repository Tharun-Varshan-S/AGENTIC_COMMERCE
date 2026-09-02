from sqlalchemy import Column, String, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class Merchant(BaseModel):
    __tablename__ = "merchants"

    name = Column(String, nullable=False)
    description = Column(String)
    email = Column(String, nullable=False)
    currency = Column(String, default="INR", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # AI Commerce settings
    ai_commerce_enabled = Column(Boolean, default=True, nullable=False)
    ai_discount_percent = Column(Numeric(5, 2), default=0.0)
    agent_purchases_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    products = relationship("Product", back_populates="merchant", cascade="all, delete-orphan")
    offers = relationship("Offer", back_populates="merchant", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="merchant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="merchant", cascade="all, delete-orphan")
    rules = relationship("MerchantRule", back_populates="merchant", cascade="all, delete-orphan")
    agent_decisions = relationship("AgentDecision", back_populates="merchant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="merchant", cascade="all, delete-orphan")
    api_keys = relationship("MerchantAPIKey", back_populates="merchant", cascade="all, delete-orphan")

class MerchantRule(BaseModel):
    __tablename__ = "merchant_rules"

    merchant_id = Column(ForeignKey("merchants.id"), nullable=False, index=True)
    max_transaction_amount = Column(Numeric(10, 2))
    max_discount_percent = Column(Numeric(5, 2))
    min_margin_percent = Column(Numeric(5, 2))
    auto_approval_limit = Column(Numeric(10, 2))
    require_consent = Column(Boolean, default=True)

    merchant = relationship("Merchant", back_populates="rules")

class MerchantAPIKey(BaseModel):
    __tablename__ = "merchant_api_keys"

    merchant_id = Column(ForeignKey("merchants.id"), nullable=False, index=True)
    key_hash = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    merchant = relationship("Merchant", back_populates="api_keys")

from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class AgenticPaymentAuthorization(BaseModel):
    __tablename__ = "agentic_payment_authorizations"

    customer_id = Column(ForeignKey("customers.id"), nullable=False, index=True)
    provider = Column(String, nullable=False) # e.g. razorpay
    rail = Column(String, nullable=False) # e.g. upi_reserve_pay
    authorization_reference = Column(String, nullable=True) # Reference id from payment provider
    status = Column(String, default="ACTIVE", nullable=False) # ACTIVE, REVOKED, EXPIRED
    
    per_transaction_limit = Column(Numeric(10, 2), nullable=False)
    daily_limit = Column(Numeric(10, 2), nullable=False)
    spent_today = Column(Numeric(10, 2), default=0)
    
    expires_at = Column(DateTime(timezone=True), nullable=True)

    customer = relationship("Customer")

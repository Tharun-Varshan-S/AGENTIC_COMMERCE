from sqlalchemy import Column, String, Numeric, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class ConsentRequest(BaseModel):
    __tablename__ = "consent_requests"

    merchant_id = Column(ForeignKey("merchants.id"), nullable=False, index=True)
    customer_id = Column(ForeignKey("customers.id"), nullable=False, index=True)
    cart_id = Column(ForeignKey("carts.id"), nullable=False, index=True)
    policy_decision = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String, default="PENDING", nullable=False) # PENDING, APPROVED, DECLINED, EXPIRED
    expires_at = Column(DateTime(timezone=True), nullable=False)
    responded_at = Column(DateTime(timezone=True), nullable=True)

    merchant = relationship("Merchant")
    customer = relationship("Customer")
    cart = relationship("Cart")

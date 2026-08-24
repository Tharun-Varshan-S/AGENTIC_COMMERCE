from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class AuditLog(BaseModel):
    __tablename__ = "audit_logs"

    merchant_id = Column(ForeignKey("merchants.id"), index=True)
    customer_id = Column(ForeignKey("customers.id"), index=True)
    order_id = Column(ForeignKey("orders.id"), index=True)
    event_type = Column(String, nullable=False, index=True)
    actor_type = Column(String, nullable=False) # CUSTOMER, AI_AGENT, MERCHANT, SYSTEM
    action = Column(String, nullable=False)
    metadata_json = Column("metadata", JSONB)

    merchant = relationship("Merchant", back_populates="audit_logs")
    customer = relationship("Customer", viewonly=True)
    order = relationship("Order", back_populates="audit_logs")

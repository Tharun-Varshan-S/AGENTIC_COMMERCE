from sqlalchemy import Column, String, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class AgentDecision(BaseModel):
    __tablename__ = "agent_decisions"

    customer_id = Column(ForeignKey("customers.id"), nullable=False, index=True)
    merchant_id = Column(ForeignKey("merchants.id"), nullable=False, index=True)
    session_id = Column(String, index=True)
    intent = Column(String)
    primary_product_id = Column(ForeignKey("products.id"), index=True)
    intervention_type = Column(String, default="NONE") # NONE, UPSELL, CROSS_SELL, ALTERNATIVE
    recommended_product_id = Column(ForeignKey("products.id"), index=True)
    reason = Column(String)
    expected_order_value = Column(Numeric(10, 2))
    score = Column(Numeric(5, 4))
    scoring_details = Column(JSONB)

    # Policy and General Logging Fields
    action = Column(String)
    actor_type = Column(String)
    decision_type = Column(String)
    decision_status = Column(String)
    policy_rules = Column(JSONB)

    customer = relationship("Customer", back_populates="agent_decisions")
    merchant = relationship("Merchant", back_populates="agent_decisions")
    primary_product = relationship("Product", foreign_keys=[primary_product_id], back_populates="agent_decisions_primary")
    recommended_product = relationship("Product", foreign_keys=[recommended_product_id], back_populates="agent_decisions_recommended")

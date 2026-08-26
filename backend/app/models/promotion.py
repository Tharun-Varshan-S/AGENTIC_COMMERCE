from sqlalchemy import Column, String, Numeric, ForeignKey, Integer, DateTime
from sqlalchemy.orm import relationship
from app.db.base_class import BaseModel

class Promotion(BaseModel):
    __tablename__ = "promotions"

    merchant_id = Column(ForeignKey("merchants.id"), nullable=False, index=True)
    product_id = Column(ForeignKey("products.id"), nullable=False, index=True)
    budget = Column(Numeric(10, 2), nullable=False)
    remaining_budget = Column(Numeric(10, 2), nullable=False)
    priority = Column(Integer, default=1)
    status = Column(String, default="ACTIVE", index=True)
    
    target_category = Column(String)
    target_keywords = Column(String)
    
    impressions = Column(Integer, default=0)
    agent_recommendations = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)

    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    merchant = relationship("Merchant")
    product = relationship("Product", back_populates="promotions")

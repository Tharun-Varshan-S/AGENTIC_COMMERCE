from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

class RevenueRecommendationRequest(BaseModel):
    merchant_id: UUID
    customer_id: UUID
    primary_product_id: UUID
    customer_intent: str
    customer_budget: Optional[Decimal] = None

class ProductSummary(BaseModel):
    id: UUID
    name: str
    price: Decimal

class ExplanationFactor(BaseModel):
    name: str
    score: float
    explanation: str

class RevenueRecommendationResponse(BaseModel):
    primary_product: ProductSummary
    intervention: str # CROSS_SELL, UPSELL, ALTERNATIVE, NONE
    recommended_product: Optional[ProductSummary]
    reason: str
    score: float
    expected_order_value: Decimal
    additional_revenue: Decimal
    factors: List[ExplanationFactor]

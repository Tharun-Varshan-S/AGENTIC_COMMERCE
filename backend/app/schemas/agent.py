from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID
from decimal import Decimal
from app.schemas.core import ORMBase, ProductResponse

class AgentDecisionResponse(ORMBase):
    customer_id: UUID
    merchant_id: UUID
    session_id: Optional[str] = None
    intent: Optional[str] = None
    primary_product_id: Optional[UUID] = None
    intervention_type: str
    recommended_product_id: Optional[UUID] = None
    reason: Optional[str] = None
    expected_order_value: Optional[Decimal] = None
    
    primary_product: Optional[ProductResponse] = None
    recommended_product: Optional[ProductResponse] = None

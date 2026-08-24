from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
from datetime import datetime
from app.policy.schemas import PolicyReason

class ConsentRequestInput(BaseModel):
    merchant_id: str
    customer_id: str
    cart_id: str

class ConsentRequestResponse(BaseModel):
    status: str
    decision: Optional[str] = None
    consent_id: Optional[str] = None
    amount: Optional[Decimal] = None
    message: Optional[str] = None
    reasons: Optional[List[PolicyReason]] = None
    
    class Config:
        from_attributes = True

class ConsentModelResponse(BaseModel):
    id: str
    merchant_id: str
    customer_id: str
    cart_id: str
    policy_decision: str
    amount: Decimal
    status: str
    expires_at: datetime
    responded_at: Optional[datetime] = None

    class Config:
        from_attributes = True

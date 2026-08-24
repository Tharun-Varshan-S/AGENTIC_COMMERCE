from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

class PolicyReason(BaseModel):
    code: str
    message: str

class PolicyDecision(BaseModel):
    decision: str  # ALLOWED, REQUIRES_CONSENT, REJECTED
    allowed: bool
    requires_consent: bool
    reasons: List[PolicyReason]
    cart_total: Decimal
    auto_approval_limit: Optional[Decimal] = None

class PolicyEvaluationRequest(BaseModel):
    merchant_id: str
    customer_id: str
    cart_id: str

from typing import Dict, Any, Type
from pydantic import BaseModel
from app.tools.base import CommerceTool
from app.policy.schemas import PolicyEvaluationRequest, PolicyDecision
from app.policy.service import PolicyService
from app.db.session import SessionLocal

class ValidatePolicyInput(BaseModel):
    merchant_id: str
    customer_id: str
    cart_id: str

class ValidatePolicyTool(CommerceTool):
    name: str = "validate_policy"
    description: str = (
        "Validates the current cart against the merchant's business policies. "
        "Returns whether the transaction is ALLOWED, REQUIRES_CONSENT, or REJECTED."
    )
    input_schema: Type[BaseModel] = ValidatePolicyInput

    def execute(self, db_session, **kwargs) -> Dict[str, Any]:
        req = PolicyEvaluationRequest(**kwargs)
        db = db_session
        service = PolicyService(db)
        decision: PolicyDecision = service.evaluate(req)
        
        reasons = [{"code": r.code, "message": r.message} for r in decision.reasons]
        
        return {
            "decision": decision.decision,
            "requires_consent": decision.requires_consent,
            "reasons": reasons
        }

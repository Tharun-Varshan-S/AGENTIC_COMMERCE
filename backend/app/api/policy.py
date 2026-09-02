from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)
from app.db.session import get_db
from app.policy.schemas import PolicyEvaluationRequest, PolicyDecision
from app.policy.service import PolicyService
from app.policy.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/policy", tags=["Policy Engine"])

from app.api.auth import get_current_customer_user, verify_customer_ownership, resolve_customer
from app.models.user import User

@router.post("/evaluate", response_model=PolicyDecision)
def evaluate_policy(request: PolicyEvaluationRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    request.customer_id = str(customer.id)
    service = PolicyService(db)
    try:
        decision = service.evaluate(request)
        return decision
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in evaluate_policy")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

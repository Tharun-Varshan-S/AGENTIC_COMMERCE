from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.policy.schemas import PolicyEvaluationRequest, PolicyDecision
from app.policy.service import PolicyService
from app.policy.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/policy", tags=["Policy Engine"])

@router.post("/evaluate", response_model=PolicyDecision)
def evaluate_policy(request: PolicyEvaluationRequest, db: Session = Depends(get_db)):
    service = PolicyService(db)
    try:
        decision = service.evaluate(request)
        return decision
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

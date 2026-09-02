from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)
from app.db.session import get_db
from app.consent.schemas import ConsentRequestInput, ConsentRequestResponse
from app.consent.service import ConsentService
from app.policy.exceptions import ResourceNotFoundError
from app.api.auth import get_current_customer_user, verify_customer_ownership, resolve_customer
from app.models.user import User

router = APIRouter(prefix="/consent", tags=["Consent Engine"])

@router.post("/request", response_model=ConsentRequestResponse)
def request_consent(request: ConsentRequestInput, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    request.customer_id = str(customer.id)
    service = ConsentService(db)
    try:
        response = service.request_consent(request)
        return response
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in request_consent")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post("/{consent_id}/approve", response_model=ConsentRequestResponse)
def approve_consent(consent_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    from app.models.consent import ConsentRequest
    consent_req = db.query(ConsentRequest).filter(ConsentRequest.id == consent_id).first()
    if not consent_req:
        raise HTTPException(status_code=404, detail="Consent request not found")
    verify_customer_ownership(db, str(consent_req.customer_id), current_user)

    service = ConsentService(db)
    try:
        response = service.approve(consent_id)
        if response.status == "ERROR":
            raise HTTPException(status_code=400, detail=response.message)
        return response
    except Exception as e:
        logger.exception("Unexpected error in approve_consent")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post("/{consent_id}/decline", response_model=ConsentRequestResponse)
def decline_consent(consent_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    from app.models.consent import ConsentRequest
    consent_req = db.query(ConsentRequest).filter(ConsentRequest.id == consent_id).first()
    if not consent_req:
        raise HTTPException(status_code=404, detail="Consent request not found")
    verify_customer_ownership(db, str(consent_req.customer_id), current_user)

    service = ConsentService(db)
    try:
        response = service.decline(consent_id)
        if response.status == "ERROR":
            raise HTTPException(status_code=400, detail=response.message)
        return response
    except Exception as e:
        logger.exception("Unexpected error in decline_consent")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

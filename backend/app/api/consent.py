from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.consent.schemas import ConsentRequestInput, ConsentRequestResponse
from app.consent.service import ConsentService
from app.policy.exceptions import ResourceNotFoundError

router = APIRouter(prefix="/consent", tags=["Consent Engine"])

@router.post("/request", response_model=ConsentRequestResponse)
def request_consent(request: ConsentRequestInput, db: Session = Depends(get_db)):
    service = ConsentService(db)
    try:
        response = service.request_consent(request)
        return response
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{consent_id}/approve", response_model=ConsentRequestResponse)
def approve_consent(consent_id: str, db: Session = Depends(get_db)):
    service = ConsentService(db)
    try:
        response = service.approve(consent_id)
        if response.status == "ERROR":
            raise HTTPException(status_code=400, detail=response.message)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{consent_id}/decline", response_model=ConsentRequestResponse)
def decline_consent(consent_id: str, db: Session = Depends(get_db)):
    service = ConsentService(db)
    try:
        response = service.decline(consent_id)
        if response.status == "ERROR":
            raise HTTPException(status_code=400, detail=response.message)
        return response
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

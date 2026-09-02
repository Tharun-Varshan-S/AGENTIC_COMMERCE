from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.payment.razorpay_client import verify_webhook_signature
from app.payment.exceptions import WebhookVerificationError
from app.payment.service import process_webhook
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/razorpay")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")
        
    try:
        verify_webhook_signature(body, signature)
    except WebhookVerificationError as e:
        logger.error(f"Webhook signature verification failed: {str(e)}")
        from app.models.audit import AuditLog
        audit = AuditLog(
            action="WEBHOOK_SIGNATURE_MISMATCH",
            event_type="security",
            actor_type="EXTERNAL",
            metadata_json={"error": str(e), "headers": dict(request.headers)}
        )
        db.add(audit)
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid signature")
        
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
        
    try:
        res = process_webhook(db, payload)
        return res
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        # Return 200 even on some processing errors to prevent Razorpay from retrying endlessly if it's a non-transient error,
        # but for true infrastructure errors we might want a 500. For this MVP, return 500 so it retries.
        raise HTTPException(status_code=500, detail="Internal processing error")

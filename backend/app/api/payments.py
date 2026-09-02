from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import logging
from typing import Optional

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.payment.service import create_payment_order, verify_payment, create_direct_payment_order
from app.payment.agentic_service import setup_agentic_authorization, get_active_authorization, revoke_authorization, execute_agentic_payment, execute_direct_agentic_payment
from app.payment.exceptions import PaymentStateError, PaymentVerificationError
from app.payment.schemas import RazorpayOrderRequest, RazorpayVerifyRequest, PaymentStatusResponse, DirectCheckoutRequest, AgenticSetupRequest, ExecuteAgenticRequest
from pydantic import BaseModel
from decimal import Decimal
from app.api.auth import get_current_customer_user, verify_customer_ownership, resolve_customer
from app.models.user import User

router = APIRouter()

@router.post("/create-order")
def create_order(request: RazorpayOrderRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    if not request.human_approval:
        raise HTTPException(status_code=400, detail="Human approval is required to create a payment order.")
    try:
        res = create_payment_order(
            db, 
            request.merchant_id, 
            str(customer.id),
            request.cart_id,
            request.source,
            request.agent_trace,
            request.human_approval
        )
        return res
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in create_order")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post("/create-direct-order")
def create_direct_order(request: DirectCheckoutRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    if not request.human_approval:
        raise HTTPException(status_code=400, detail="Human approval is required to create a direct payment order.")
    try:
        request.customer_id = str(customer.id)
        res = create_direct_payment_order(db, request)
        return res
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in create_direct_order")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post("/verify")
def verify_payment_route(request: RazorpayVerifyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    from app.models.order import Payment
    payment = db.query(Payment).filter(Payment.id == request.payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    verify_customer_ownership(db, str(payment.order.customer_id), current_user)
    
    try:
        res = verify_payment(
            db, 
            request.payment_id, 
            request.razorpay_payment_id, 
            request.razorpay_order_id, 
            request.razorpay_signature
        )
        return res
    except PaymentVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in verify_payment_route")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post("/authorization/setup")
def setup_agentic(request: AgenticSetupRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    try:
        auth = setup_agentic_authorization(
            db, 
            request.merchant_id,
            str(customer.id), 
            Decimal(str(request.per_transaction_limit)), 
            Decimal(str(request.daily_limit))
        )
        return {
            "id": auth.id,
            "status": auth.status,
            "rail": auth.rail,
            "per_transaction_limit": auth.per_transaction_limit,
            "daily_limit": auth.daily_limit,
            "spent_today": auth.spent_today
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in setup_agentic")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.get("/authorization/status")
def status_agentic(merchant_id: str, customer_id: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, merchant_id, customer_id)
    auth = get_active_authorization(db, str(customer.id))
    if not auth:
        return {"status": "none"}
    return {
        "id": auth.id,
        "status": auth.status,
        "rail": auth.rail,
        "per_transaction_limit": auth.per_transaction_limit,
        "daily_limit": auth.daily_limit,
        "spent_today": auth.spent_today
    }

@router.post("/authorization/revoke")
def revoke_agentic(merchant_id: str, customer_id: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, merchant_id, customer_id)
    auth = get_active_authorization(db, str(customer.id))
    if not auth:
        raise HTTPException(status_code=404, detail="Active authorization not found")
    revoke_authorization(db, str(auth.id))
    return {"status": "revoked"}

@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
def get_payment_status(payment_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    from app.models.order import Payment
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    verify_customer_ownership(db, str(payment.order.customer_id), current_user)
    return {"payment_id": payment.id, "status": payment.status}

@router.post("/execute-agentic")
def execute_agentic(request: ExecuteAgenticRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    try:
        res = execute_agentic_payment(db, request.merchant_id, str(customer.id), request.cart_id)
        return res
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in execute_agentic")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

class ExecuteDirectAgenticRequest(BaseModel):
    merchant_id: str
    customer_id: Optional[str] = None
    offer_id: str
    quantity: int = 1

@router.post("/execute-direct-agentic")
def execute_direct_agentic(request: ExecuteDirectAgenticRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    try:
        res = execute_direct_agentic_payment(db, request.merchant_id, str(customer.id), request.offer_id, request.quantity)
        return res
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in execute_direct_agentic")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

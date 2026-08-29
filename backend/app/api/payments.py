from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.payment.service import create_payment_order, verify_payment, create_direct_payment_order
from app.payment.agentic_service import setup_agentic_authorization, get_active_authorization, revoke_authorization, execute_agentic_payment
from app.payment.exceptions import PaymentStateError, PaymentVerificationError
from app.payment.schemas import RazorpayOrderRequest, RazorpayVerifyRequest, PaymentStatusResponse, DirectCheckoutRequest, AgenticSetupRequest, ExecuteAgenticRequest
from decimal import Decimal

router = APIRouter()

@router.post("/create-order")
def create_order(request: RazorpayOrderRequest, db: Session = Depends(get_db)):
    if not request.human_approval:
        raise HTTPException(status_code=400, detail="Human approval is required to create a payment order.")
    try:
        res = create_payment_order(
            db, 
            request.merchant_id, 
            request.customer_id,
            request.cart_id,
            request.source,
            request.agent_trace,
            request.human_approval
        )
        return res
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/create-direct-order")
def create_direct_order(request: DirectCheckoutRequest, db: Session = Depends(get_db)):
    if not request.human_approval:
        raise HTTPException(status_code=400, detail="Human approval is required to create a direct payment order.")
    try:
        res = create_direct_payment_order(db, request)
        return res
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/verify")
def verify_payment_route(request: RazorpayVerifyRequest, db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
def get_payment_status(payment_id: str, db: Session = Depends(get_db)):
    from app.models.order import Payment
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"payment_id": payment.id, "status": payment.status}

@router.post("/authorization/setup")
def setup_agentic(request: AgenticSetupRequest, db: Session = Depends(get_db)):
    try:
        auth = setup_agentic_authorization(
            db, 
            request.customer_id, 
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/authorization/status")
def status_agentic(customer_id: str, db: Session = Depends(get_db)):
    auth = get_active_authorization(db, customer_id)
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
def revoke_agentic(customer_id: str, db: Session = Depends(get_db)):
    auth = get_active_authorization(db, customer_id)
    if not auth:
        raise HTTPException(status_code=404, detail="Active authorization not found")
    revoke_authorization(db, str(auth.id))
    return {"status": "revoked"}

@router.post("/execute-agentic")
def execute_agentic(request: ExecuteAgenticRequest, db: Session = Depends(get_db)):
    try:
        res = execute_agentic_payment(db, request.merchant_id, request.customer_id, request.cart_id)
        return res
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

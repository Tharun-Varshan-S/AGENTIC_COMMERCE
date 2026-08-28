from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.payment.schemas import RazorpayOrderRequest, RazorpayVerifyRequest, PaymentStatusResponse
from app.payment.service import create_payment_order, verify_payment
from app.payment.exceptions import PaymentStateError, PaymentVerificationError

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
            request.agent_trace
        )
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

from typing import Type, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.tools.base import CommerceTool, ToolError
from app.payment.service import create_payment_order
from app.payment.agentic_service import get_active_authorization, execute_agentic_payment
from app.models.order import Payment

class CreateRazorpayOrderInput(BaseModel):
    merchant_id: str = Field(..., description="The ID of the merchant")
    customer_id: str = Field(..., description="The ID of the customer")
    cart_id: str = Field(..., description="The ID of the active cart")

class CreateRazorpayOrderTool(CommerceTool):
    name = "create_razorpay_order"
    description = "Creates a Razorpay order for the customer's cart. Must only be called after validate_policy returns ALLOWED."
    input_schema: Type[BaseModel] = CreateRazorpayOrderInput
    read_only = False

    def execute(self, db_session: Session, **kwargs) -> Dict[str, Any]:
        try:
            res = create_payment_order(db_session, kwargs["merchant_id"], kwargs["customer_id"], kwargs["cart_id"], human_approval=False)
            return res
        except Exception as e:
            raise ToolError("PAYMENT_ORDER_FAILED", str(e))

class GetPaymentStatusInput(BaseModel):
    merchant_id: str = Field(..., description="The ID of the merchant")
    customer_id: str = Field(..., description="The ID of the customer")
    payment_id: str = Field(..., description="The ID of the payment")

class GetPaymentStatusTool(CommerceTool):
    name = "get_payment_status"
    description = "Checks the status of a payment (CREATED, CAPTURED, FAILED, etc.)"
    input_schema: Type[BaseModel] = GetPaymentStatusInput
    read_only = True

    def execute(self, db_session: Session, **kwargs) -> Dict[str, Any]:
        payment = db_session.query(Payment).filter(Payment.id == kwargs["payment_id"]).first()
        if not payment:
            raise ToolError("PAYMENT_NOT_FOUND", "Payment not found")
        return {"payment_id": payment.id, "status": payment.status}

class CheckPaymentAuthorizationInput(BaseModel):
    customer_id: str = Field(..., description="The ID of the customer")

class CheckPaymentAuthorizationTool(CommerceTool):
    name = "check_payment_authorization"
    description = "Checks if the customer has an active Agentic Payment capability configured, and returns the limits."
    input_schema: Type[BaseModel] = CheckPaymentAuthorizationInput
    read_only = True

    def execute(self, db_session: Session, **kwargs) -> Dict[str, Any]:
        auth = get_active_authorization(db_session, kwargs["customer_id"])
        if not auth:
            return {"status": "none", "message": "No active agentic payment authorization."}
        return {
            "status": auth.status,
            "rail": auth.rail,
            "per_transaction_limit": float(auth.per_transaction_limit),
            "daily_limit": float(auth.daily_limit),
            "spent_today": float(auth.spent_today),
            "expires_at": str(auth.expires_at) if auth.expires_at else None
        }

class ExecuteAgenticPaymentInput(BaseModel):
    merchant_id: str = Field(..., description="The ID of the merchant")
    customer_id: str = Field(..., description="The ID of the customer")
    cart_id: str = Field(..., description="The ID of the active cart")

class ExecuteAgenticPaymentTool(CommerceTool):
    name = "execute_agentic_payment"
    description = "Executes an authorized agentic payment directly on the backend. Requires prior human approval or consent."
    input_schema: Type[BaseModel] = ExecuteAgenticPaymentInput
    read_only = False

    def execute(self, db_session: Session, **kwargs) -> Dict[str, Any]:
        try:
            res = execute_agentic_payment(db_session, kwargs["merchant_id"], kwargs["customer_id"], kwargs["cart_id"])
            return res
        except Exception as e:
            raise ToolError("AGENTIC_PAYMENT_FAILED", str(e))

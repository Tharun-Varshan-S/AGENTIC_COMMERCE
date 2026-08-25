from typing import Type, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.tools.base import CommerceTool, ToolError
from app.payment.service import create_payment_order
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
            res = create_payment_order(db_session, kwargs["merchant_id"], kwargs["customer_id"], kwargs["cart_id"])
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

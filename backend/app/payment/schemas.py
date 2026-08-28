from pydantic import BaseModel
from typing import Optional

class RazorpayOrderRequest(BaseModel):
    merchant_id: str
    customer_id: str
    cart_id: str
    human_approval: bool = False
    source: str = "DIRECT"
    agent_trace: Optional[dict] = None

class RazorpayOrderResponse(BaseModel):
    payment_id: str
    razorpay_order_id: str
    razorpay_key_id: str
    amount: int
    currency: str

class RazorpayVerifyRequest(BaseModel):
    payment_id: str
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str

class PaymentStatusResponse(BaseModel):
    payment_id: str
    status: str

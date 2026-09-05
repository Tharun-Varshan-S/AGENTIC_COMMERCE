from pydantic import BaseModel
from typing import Optional

class RazorpayOrderRequest(BaseModel):
    merchant_id: str
    customer_id: Optional[str] = None
    cart_id: str
    human_approval: bool = False
    source: str = "DIRECT"
    agent_trace: Optional[dict] = None

class DirectCheckoutRequest(BaseModel):
    merchant_id: str
    customer_id: Optional[str] = None
    product_id: str
    offer_id: str
    quantity: int = 1
    source: str = "DIRECT"
    human_approval: bool = False
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

class AgenticSetupRequest(BaseModel):
    merchant_id: str
    customer_id: Optional[str] = None
    per_transaction_limit: float
    daily_limit: float

class ExecuteAgenticRequest(BaseModel):
    merchant_id: str
    customer_id: Optional[str] = None
    cart_id: str

class PaymentHistoryItem(BaseModel):
    id: str
    local_order_id: str
    razorpay_order_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    amount: float
    currency: str
    status: str
    webhook_verified: bool
    created_at: str

    class Config:
        orm_mode = True

class PaymentHistoryResponse(BaseModel):
    payments: list[PaymentHistoryItem]


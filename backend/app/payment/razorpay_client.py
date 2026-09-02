import os
import razorpay
from .exceptions import PaymentVerificationError, WebhookVerificationError

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "")

client = None
if RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET:
    client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

def create_order(amount_paise: int, currency: str = "INR", receipt: str = None, notes: dict = None) -> dict:
    """
    Creates a Razorpay order. Returns the dict representing the created order.
    amount_paise must be integer.
    """
    if not client:
        raise RuntimeError("Razorpay API keys are not configured. Cannot create orders.")

    data = {
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt,
        "notes": notes or {}
    }
    return client.order.create(data=data)

def verify_payment_signature(razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str):
    """
    Verifies the payment signature returned by the frontend.
    Raises PaymentVerificationError if invalid.
    """
    if not client:
        raise PaymentVerificationError("No Razorpay client configured for verification. Verification rejected securely.")

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }
    try:
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError as e:
        raise PaymentVerificationError(str(e))

def verify_webhook_signature(body: bytes, signature: str):
    """
    Verifies the webhook signature.
    Raises WebhookVerificationError if invalid.
    """
    if not client:
        raise WebhookVerificationError("No Razorpay client configured for webhook verification. Verification rejected securely.")
        
    try:
        client.utility.verify_webhook_signature(body.decode('utf-8'), signature, RAZORPAY_WEBHOOK_SECRET)
    except razorpay.errors.SignatureVerificationError as e:
        raise WebhookVerificationError(str(e))

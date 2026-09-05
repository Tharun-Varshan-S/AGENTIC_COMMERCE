import os
import razorpay
from .exceptions import PaymentVerificationError, WebhookVerificationError, RazorpayProviderError

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
        raise RazorpayProviderError("Razorpay API keys are not configured. Cannot create orders.")

    data = {
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt,
        "notes": notes or {}
    }
    try:
        return client.order.create(data=data)
    except razorpay.errors.RazorpayError as e:
        import logging
        logging.error(f"Razorpay API Error during create_order: {str(e)}")
        raise RazorpayProviderError(f"Razorpay payment provider failed: {str(e)}")

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

def get_or_create_customer(name: str, email: str = None, contact: str = "9999999999") -> str:
    """
    Creates a Razorpay customer if needed. In a production scenario, we'd search first,
    but for simplicity and since we store the ID, we'll just create it.
    """
    if not client:
        raise RazorpayProviderError("Razorpay API keys not configured.")
    data = {
        "name": name,
        "contact": contact
    }
    if email:
        data["email"] = email
    cust = client.customer.create(data=data)
    return cust["id"]

def create_mandate_order(customer_id: str, max_amount_paise: int, expire_at_ts: int, receipt: str, currency: str = "INR") -> dict:
    """
    Creates a Razorpay order for UPI Mandate (TokenHQ SBMD) registration.
    """
    if not client:
        raise RazorpayProviderError("Razorpay API keys not configured.")
    
    data = {
        "amount": 0, # Amount 0 for mandate registration
        "currency": currency,
        "method": "upi",
        "customer_id": customer_id,
        "receipt": receipt,
        "token": {
            "max_amount": max_amount_paise,
            "expire_at": expire_at_ts,
            "frequency": "as_presented"
        }
    }
    try:
        return client.order.create(data=data)
    except razorpay.errors.RazorpayError as e:
        import logging
        logging.error(f"Razorpay API Error during create_mandate_order: {str(e)}")
        raise RazorpayProviderError(f"Razorpay payment provider failed: {str(e)}")

def create_recurring_payment(amount_paise: int, customer_id: str, token_id: str, order_id: str, currency: str = "INR", description: str = "Agentic Payment") -> dict:
    """
    Executes a recurring payment against a registered mandate token.
    """
    if not client:
        raise RazorpayProviderError("Razorpay API keys not configured.")

    data = {
        "amount": amount_paise,
        "currency": currency,
        "customer_id": customer_id,
        "token": token_id,
        "recurring": "1",
        "description": description,
        "order_id": order_id
    }
    try:
        return client.payment.create(data=data)
    except razorpay.errors.RazorpayError as e:
        import logging
        logging.error(f"Razorpay API Error during create_recurring_payment: {str(e)}")
        raise RazorpayProviderError(f"Razorpay payment provider failed: {str(e)}")


def charge_saved_instrument(
    order_id: str,
    razorpay_customer_id: str,
    token_id: str,
    amount_paise: int,
    email: str,
    contact: str = "9999999999",
    description: str = "Agentic Commerce — Agent-Driven Purchase"
) -> dict:
    """
    Headless S2S charge against a pre-authorized saved payment instrument.
    Uses Razorpay's recurring/tokenized payment API — no checkout UI required.
    This is the core of the agentic headless payment flow.

    Returns the Razorpay payment dict (status may be 'created' or 'authorized').
    Caller must poll/capture separately.

    Raises:
        SavedInstrumentInvalid — if the token is expired/revoked
        ChargeDeclined — if the issuer explicitly declines
        RazorpayProviderError — for any other Razorpay API failure
    """
    from .exceptions import SavedInstrumentInvalid, ChargeDeclined
    if not client:
        raise RazorpayProviderError("Razorpay API keys not configured.")

    data = {
        "email": email,
        "contact": contact,
        "amount": amount_paise,
        "currency": "INR",
        "order_id": order_id,
        "customer_id": razorpay_customer_id,
        "token": token_id,
        "recurring": "1",
        "description": description,
        "notes": {
            "instrument_mode": "headless_s2s",
            "agent": "agentic_commerce_agent"
        }
    }
    import logging
    log = logging.getLogger(__name__)
    try:
        result = client.payment.createRecurring(data)
        log.info(f"charge_saved_instrument: order={order_id} token={token_id} result_status={result.get('status')}")
        return result
    except razorpay.errors.RazorpayError as e:
        err_str = str(e).lower()
        log.error(f"charge_saved_instrument failed: {e}")
        # Distinguish token-invalid from issuer-decline from provider error
        if any(k in err_str for k in ["token", "invalid", "expired", "not found", "authentication"]):
            raise SavedInstrumentInvalid(f"Saved payment instrument is invalid or expired: {e}")
        if any(k in err_str for k in ["declined", "insufficient", "do not honor", "restricted"]):
            raise ChargeDeclined(f"Card issuer declined the charge: {e}")
        raise RazorpayProviderError(f"Razorpay provider error during S2S charge: {e}")


def capture_payment(razorpay_payment_id: str, amount_paise: int, currency: str = "INR") -> dict:
    """
    Explicitly captures an authorized Razorpay payment.
    Required when payment_capture is not set to automatic on the order.
    """
    if not client:
        raise RazorpayProviderError("Razorpay API keys not configured.")
    try:
        return client.payment.capture(razorpay_payment_id, amount_paise, {"currency": currency})
    except razorpay.errors.RazorpayError as e:
        raise RazorpayProviderError(f"Failed to capture payment {razorpay_payment_id}: {e}")


def fetch_payment(razorpay_payment_id: str) -> dict:
    """
    Fetches the current state of a Razorpay payment.
    Used to poll for status after a recurring charge.
    """
    if not client:
        raise RazorpayProviderError("Razorpay API keys not configured.")
    try:
        return client.payment.fetch(razorpay_payment_id)
    except razorpay.errors.RazorpayError as e:
        raise RazorpayProviderError(f"Failed to fetch payment {razorpay_payment_id}: {e}")


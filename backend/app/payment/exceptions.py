class PaymentVerificationError(Exception):
    """Raised when payment verification fails (e.g., signature mismatch)."""
    pass

class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""
    pass

class PaymentStateError(Exception):
    """Raised when a payment operation is attempted in an invalid state."""
    pass

class AmountMismatchError(Exception):
    """Raised when the expected amount does not match the payment amount."""
    pass

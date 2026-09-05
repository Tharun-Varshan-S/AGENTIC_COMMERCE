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

class AgentAuthorizationError(Exception):
    pass

class TransactionLimitExceeded(Exception):
    pass

class DailyLimitExceeded(Exception):
    pass

class InsufficientInventory(Exception):
    pass

class MerchantInactive(Exception):
    pass

class RazorpayProviderError(Exception):
    """Raised when the Razorpay API returns an error or is unreachable.
    Signals a provider-side failure, not a logic/validation error.
    """
    pass

class SpendingLimitNotConfigured(Exception):
    """Raised when a customer has not explicitly set a spending limit."""
    pass

class SavedInstrumentInvalid(Exception):
    """Raised when the saved Razorpay token is expired, revoked, or not found.
    Prompts the user to re-authorize their payment method on the Profile page.
    """
    pass

class ChargeDeclined(Exception):
    """Raised when a recurring/S2S charge is explicitly declined by the card issuer.
    This is a graceful, expected failure path that must be surfaced in the audit trail
    and shown clearly in the UI with a user-friendly message.
    """
    pass

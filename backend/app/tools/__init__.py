from app.tools.registry import registry
from app.tools.multi_source_tools import CreateCheckoutSessionTool
from app.tools.cart_tools import CalculateCartTool, ValidateCartTool
from app.tools.payment_tools import GetPaymentStatusTool
from app.tools.policy_tools import ValidatePolicyTool

registry.register(CreateCheckoutSessionTool())
registry.register(CalculateCartTool())
registry.register(ValidateCartTool())
registry.register(GetPaymentStatusTool())
registry.register(ValidatePolicyTool())

__all__ = ["registry"]

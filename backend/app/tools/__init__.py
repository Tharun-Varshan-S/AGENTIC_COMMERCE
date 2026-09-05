from app.tools.registry import registry
from app.tools.multi_source_tools import CreateCheckoutSessionTool
from app.tools.cart_tools import CalculateCartTool, ValidateCartTool
from app.tools.payment_tools import GetPaymentStatusTool, CreateRazorpayOrderTool, CreateDirectRazorpayOrderTool
from app.tools.policy_tools import ValidatePolicyTool

from app.tools.revenue_tools import GetRevenueRecommendationTool, SuggestUpsellTool

registry.register(CreateCheckoutSessionTool())
registry.register(CalculateCartTool())
registry.register(ValidateCartTool())
registry.register(GetPaymentStatusTool())
registry.register(ValidatePolicyTool())
registry.register(SuggestUpsellTool())
registry.register(CreateRazorpayOrderTool())
registry.register(CreateDirectRazorpayOrderTool())
__all__ = ["registry"]

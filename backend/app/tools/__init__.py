from app.tools.registry import registry
from app.tools.multi_source_tools import (
    GetProductDetailsTool,
    CheckProductAvailabilityTool,
    GetMerchantPromotionTool,
    CompareProductsTool,
    RankProductsTool,
    CreateCheckoutSessionTool
)

registry.register(GetProductDetailsTool())
registry.register(CheckProductAvailabilityTool())
registry.register(GetMerchantPromotionTool())
registry.register(CompareProductsTool())
registry.register(RankProductsTool())
registry.register(CreateCheckoutSessionTool())

__all__ = ["registry"]

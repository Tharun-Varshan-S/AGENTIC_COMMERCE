from app.tools.registry import registry
from app.tools.multi_source_tools import (
    SearchAmazonCatalogTool,
    SearchFlipkartCatalogTool,
    SearchRazorpayMerchantsTool,
    GetProductDetailsTool,
    CheckProductAvailabilityTool,
    GetMerchantPromotionTool,
    CompareProductsTool,
    RankProductsTool,
    CreateCheckoutSessionTool
)

registry.register(SearchAmazonCatalogTool())
registry.register(SearchFlipkartCatalogTool())
registry.register(SearchRazorpayMerchantsTool())
registry.register(GetProductDetailsTool())
registry.register(CheckProductAvailabilityTool())
registry.register(GetMerchantPromotionTool())
registry.register(CompareProductsTool())
registry.register(RankProductsTool())
registry.register(CreateCheckoutSessionTool())

__all__ = ["registry"]

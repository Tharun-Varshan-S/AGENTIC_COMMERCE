from app.tools.registry import registry
from app.tools.catalog_tools import SearchCatalogTool, GetProductTool
from app.tools.inventory_tools import CheckInventoryTool
from app.tools.customer_tools import GetCustomerContextTool
from app.tools.cart_tools import CalculateCartTool, ValidateCartTool
from app.tools.recommendation_tools import GetRecommendationsTool
from app.tools.revenue_tools import GetRevenueRecommendationTool

registry.register(SearchCatalogTool())
registry.register(GetProductTool())
registry.register(CheckInventoryTool())
registry.register(GetCustomerContextTool())
registry.register(CalculateCartTool())
registry.register(ValidateCartTool())
registry.register(GetRecommendationsTool())
registry.register(GetRevenueRecommendationTool())

__all__ = ["registry"]

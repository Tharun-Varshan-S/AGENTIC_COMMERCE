from sqlalchemy.orm import Session
from app.tools.base import CommerceTool, ToolError
from app.tools.schemas import SearchCatalogInput, GetProductInput
from app.services.core import CoreService

class SearchCatalogTool(CommerceTool):
    name = "search_catalog"
    description = "Search the merchant's active product catalog using structured criteria."
    input_schema = SearchCatalogInput
    read_only = True

    def execute(self, db_session: Session, **kwargs):
        merchant_id = kwargs.get("merchant_id")
        query = kwargs.get("query")
        category = kwargs.get("category")
        max_price = kwargs.get("max_price")
        limit = kwargs.get("limit", 10)

        core_service = CoreService(db_session)
        products = core_service.get_products(
            category=category,
            is_active=True,
            search=query,
            max_price=max_price
        )

        # Ensure merchant isolation
        merchant_products = [p for p in products if p.merchant_id == merchant_id]
        
        # Apply limit
        merchant_products = merchant_products[:limit]

        results = []
        for p in merchant_products:
            results.append({
                "id": str(p.id),
                "sku": p.sku,
                "name": p.name,
                "description": p.description,
                "category": p.category,
                "brand": p.brand,
                "price": float(p.price) if p.price else None,
                "currency": p.currency,
                "available_quantity": p.inventory.available_quantity if p.inventory else 0
            })

        return {
            "products": results,
            "count": len(results)
        }


class GetProductTool(CommerceTool):
    name = "get_product"
    description = "Get detailed information about a specific product."
    input_schema = GetProductInput
    read_only = True

    def execute(self, db_session: Session, **kwargs):
        merchant_id = kwargs.get("merchant_id")
        product_id = kwargs.get("product_id")

        core_service = CoreService(db_session)
        product = core_service.get_product(product_id)

        if not product:
            raise ToolError("PRODUCT_NOT_FOUND", "The requested product does not exist.")

        if product.merchant_id != merchant_id:
            raise ToolError("PRODUCT_NOT_FOUND", "The requested product does not exist.")

        return {
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
            "description": product.description,
            "category": product.category,
            "brand": product.brand,
            "price": float(product.price) if product.price else None,
            "currency": product.currency,
            "available_quantity": product.inventory.available_quantity if product.inventory else 0,
            "is_active": product.is_active
        }

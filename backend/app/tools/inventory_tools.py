from sqlalchemy.orm import Session
from app.tools.base import CommerceTool, ToolError
from app.tools.schemas import CheckInventoryInput
from app.services.core import CoreService

class CheckInventoryTool(CommerceTool):
    name = "check_inventory"
    description = "Check real-time inventory status for a specific product."
    input_schema = CheckInventoryInput
    read_only = True

    def execute(self, db_session: Session, **kwargs):
        merchant_id = kwargs.get("merchant_id")
        product_id = kwargs.get("product_id")

        core_service = CoreService(db_session)
        product = core_service.get_product(product_id)

        if not product or product.merchant_id != merchant_id:
            raise ToolError("PRODUCT_NOT_FOUND", "The requested product does not exist.")

        inv = product.inventory
        if not inv:
            return {
                "product_id": str(product_id),
                "quantity": 0,
                "reserved_quantity": 0,
                "available_quantity": 0,
                "status": "OUT_OF_STOCK"
            }

        available = inv.available_quantity
        
        status = "IN_STOCK"
        if available <= 0:
            status = "OUT_OF_STOCK"
        elif available <= 5: # simple low stock threshold
            status = "LOW_STOCK"

        return {
            "product_id": str(product_id),
            "quantity": inv.quantity,
            "reserved_quantity": inv.reserved_quantity,
            "available_quantity": available,
            "status": status
        }

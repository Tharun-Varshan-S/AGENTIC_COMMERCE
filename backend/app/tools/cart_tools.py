from sqlalchemy.orm import Session
from app.tools.base import CommerceTool, ToolError
from app.tools.schemas import CalculateCartInput, ValidateCartInput
from app.services.cart import CartService

class CalculateCartTool(CommerceTool):
    name = "calculate_cart"
    description = "Authoritatively calculate the cart total for a customer."
    input_schema = CalculateCartInput
    read_only = True

    def execute(self, db_session: Session, **kwargs):
        merchant_id = kwargs.get("merchant_id")
        customer_id = kwargs.get("customer_id")

        cart_service = CartService(db_session)
        cart = cart_service.get_active_cart(customer_id)

        if not cart:
            raise ToolError("CART_NOT_FOUND", "The customer does not have an active cart.")

        if cart.merchant_id != merchant_id:
            raise ToolError("CART_NOT_FOUND", "The customer does not have an active cart.")

        items = []
        for item in cart.items:
            items.append({
                "product_id": str(item.product_id),
                "name": item.product.name if item.product else "Unknown Product",
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.unit_price * item.quantity)
            })

        return {
            "cart_id": str(cart.id),
            "items": items,
            "subtotal": float(cart.subtotal),
            "discount": 0.0,
            "total": float(cart.subtotal),
            "currency": cart.currency
        }


class ValidateCartTool(CommerceTool):
    name = "validate_cart"
    description = "Perform basic read-only commerce integrity checks on a cart."
    input_schema = ValidateCartInput
    read_only = True

    def execute(self, db_session: Session, **kwargs):
        merchant_id = kwargs.get("merchant_id")
        customer_id = kwargs.get("customer_id")

        cart_service = CartService(db_session)
        cart = cart_service.get_active_cart(customer_id)

        if not cart or cart.merchant_id != merchant_id:
            return {
                "valid": False,
                "issues": [{
                    "code": "CART_NOT_FOUND",
                    "message": "No active cart found."
                }]
            }

        issues = []
        
        if not cart.items:
            issues.append({
                "code": "EMPTY_CART",
                "message": "Cart has no items."
            })
            
        for item in cart.items:
            product = item.product
            if not product:
                issues.append({
                    "code": "PRODUCT_NOT_FOUND",
                    "product_id": str(item.product_id),
                    "message": "Product no longer exists."
                })
                continue
                
            if not product.is_active:
                issues.append({
                    "code": "PRODUCT_INACTIVE",
                    "product_id": str(product.id),
                    "message": f"Product '{product.name}' is no longer active."
                })
                
            if product.inventory:
                available = product.inventory["available_quantity"]
                if item.quantity > available:
                    issues.append({
                        "code": "INSUFFICIENT_INVENTORY",
                        "product_id": str(product.id),
                        "message": f"Only {available} units available for '{product.name}'."
                    })

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

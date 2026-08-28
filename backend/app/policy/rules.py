from typing import List, Tuple, Dict, Any
from decimal import Decimal
from app.models.merchant import MerchantRule
from app.models.order import Cart, CartItem
from app.models.product import Product, Inventory
from app.policy.schemas import PolicyReason

class PolicyRule:
    def evaluate(self, context: Dict[str, Any]) -> List[PolicyReason]:
        raise NotImplementedError()

class MaxTransactionRule(PolicyRule):
    def evaluate(self, context: Dict[str, Any]) -> List[PolicyReason]:
        cart_total: Decimal = context["cart_total"]
        merchant_rules: MerchantRule = context["merchant_rules"]
        
        if merchant_rules and merchant_rules.max_transaction_amount:
            if cart_total > merchant_rules.max_transaction_amount:
                return [PolicyReason(
                    code="TRANSACTION_LIMIT_EXCEEDED",
                    message="Transaction exceeds the merchant limit."
                )]
        return []

class InventoryRule(PolicyRule):
    def evaluate(self, context: Dict[str, Any]) -> List[PolicyReason]:
        cart_items: List[CartItem] = context["cart_items"]
        inventories: Dict[str, Inventory] = context["inventories"]
        
        reasons = []
        for item in cart_items:
            inv = inventories.get(item.product_id)
            if not inv:
                reasons.append(PolicyReason(
                    code="INSUFFICIENT_INVENTORY",
                    message=f"Inventory data not found for product {item.product_id}."
                ))
                continue
            
            available = inv.quantity - inv.reserved_quantity
            if available < item.quantity:
                reasons.append(PolicyReason(
                    code="INSUFFICIENT_INVENTORY",
                    message=f"Only {available} units are available for product {item.product_id}."
                ))
        return reasons

class ProductStatusRule(PolicyRule):
    def evaluate(self, context: Dict[str, Any]) -> List[PolicyReason]:
        cart_items: List[CartItem] = context["cart_items"]
        products: Dict[str, Product] = context["products"]
        
        reasons = []
        for item in cart_items:
            prod = products.get(item.product_id)
            if not prod or not prod.is_active:
                reasons.append(PolicyReason(
                    code="PRODUCT_INACTIVE",
                    message=f"Product {item.product_id} is inactive or not found."
                ))
        return reasons

class PriceIntegrityRule(PolicyRule):
    def evaluate(self, context: Dict[str, Any]) -> List[PolicyReason]:
        cart_items: List[CartItem] = context["cart_items"]
        products: Dict[str, Product] = context["products"]
        
        reasons = []
        for item in cart_items:
            prod = products.get(item.product_id)
            if prod and item.unit_price != prod.price:
                reasons.append(PolicyReason(
                    code="PRICE_CHANGED",
                    message=f"Price for product {item.product_id} has changed from {item.unit_price} to {prod.price}."
                ))
        return reasons

class DiscountLimitRule(PolicyRule):
    def evaluate(self, context: Dict[str, Any]) -> List[PolicyReason]:
        # Using 0% discount as Cart doesn't natively support discount percentages at item level yet
        # If implemented, we check: discount_percent > max_discount_percent
        cart: Cart = context["cart"]
        merchant_rules: MerchantRule = context["merchant_rules"]
        cart_total: Decimal = context["cart_total"]
        
        if merchant_rules and merchant_rules.max_discount_percent and cart.discount > 0 and cart_total > 0:
            discount_pct = (cart.discount / (cart_total + cart.discount)) * Decimal('100')
            if discount_pct > merchant_rules.max_discount_percent:
                return [PolicyReason(
                    code="DISCOUNT_LIMIT_EXCEEDED",
                    message=f"Discount exceeds the maximum allowed {merchant_rules.max_discount_percent}%."
                )]
        return []

class MinimumMarginRule(PolicyRule):
    def evaluate(self, context: Dict[str, Any]) -> List[PolicyReason]:
        cart_items: List[CartItem] = context["cart_items"]
        products: Dict[str, Product] = context["products"]
        merchant_rules: MerchantRule = context["merchant_rules"]
        
        if not merchant_rules or merchant_rules.min_margin_percent is None:
            return []
            
        reasons = []
        for item in cart_items:
            prod = products.get(item.product_id)
            if prod and prod.cost_price:
                margin = ((item.unit_price - prod.cost_price) / item.unit_price) * Decimal('100')
                if margin < merchant_rules.min_margin_percent:
                    reasons.append(PolicyReason(
                        code="MIN_MARGIN_VIOLATION",
                        message="Transaction violates minimum margin requirements."
                    ))
        return reasons

class ConsentRequirementRule(PolicyRule):
    def evaluate(self, context: Dict[str, Any]) -> List[PolicyReason]:
        cart_total: Decimal = context["cart_total"]
        merchant_rules: MerchantRule = context["merchant_rules"]
        
        if context.get("has_approved_consent", False):
            return []
            
        if merchant_rules and merchant_rules.auto_approval_limit:
            if cart_total > merchant_rules.auto_approval_limit:
                return [PolicyReason(
                    code="ABOVE_AUTO_APPROVAL_LIMIT",
                    message=f"Transaction exceeds the merchant's automatic approval limit of {merchant_rules.auto_approval_limit}."
                )]
        elif merchant_rules and merchant_rules.require_consent:
             return [PolicyReason(
                code="ABOVE_AUTO_APPROVAL_LIMIT",
                message="Merchant requires explicit consent for transactions."
            )]
        return []

class UserSpendingLimitRule(PolicyRule):
    def evaluate(self, context: Dict[str, Any]) -> List[PolicyReason]:
        cart_total: Decimal = context["cart_total"]
        spending_limit = context.get("spending_limit")
        
        if spending_limit and Decimal(spending_limit.daily_limit) > 0:
            # We would typically fetch today's total spending here from the db,
            # but for this MVP rule we just check if this single transaction exceeds the daily limit.
            if cart_total > Decimal(spending_limit.daily_limit):
                return [PolicyReason(
                    code="SPENDING_LIMIT_EXCEEDED",
                    message=f"Transaction exceeds the user's daily spending limit of {spending_limit.daily_limit}."
                )]
        return []

from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.order import Cart, CartItem
from app.models.merchant import Merchant, MerchantRule
from app.models.customer import Customer
from app.models.product import Product, Inventory
from app.models.offer import Offer
from app.models.consent import ConsentRequest
from app.policy.schemas import PolicyEvaluationRequest, PolicyDecision
from app.policy.evaluator import PolicyEvaluator
from app.policy.exceptions import ResourceNotFoundError

class PolicyService:
    def __init__(self, db: Session):
        self.db = db
        self.evaluator = PolicyEvaluator()

    def evaluate(self, request: PolicyEvaluationRequest) -> PolicyDecision:
        # Load necessary data deterministically
        
        merchant = self.db.query(Merchant).filter(Merchant.id == request.merchant_id).first()
        if not merchant or not merchant.is_active:
            raise ResourceNotFoundError(f"Merchant {request.merchant_id} not found or inactive")
            
        customer = self.db.query(Customer).filter(Customer.id == request.customer_id, Customer.merchant_id == request.merchant_id).first()
        if not customer:
            raise ResourceNotFoundError(f"Customer {request.customer_id} not found for this merchant")
            
        cart = self.db.query(Cart).filter(Cart.id == request.cart_id, Cart.customer_id == request.customer_id).first()
        if not cart:
            raise ResourceNotFoundError(f"Cart {request.cart_id} not found")
            
        merchant_rules = self.db.query(MerchantRule).filter(MerchantRule.merchant_id == request.merchant_id).first()
        
        cart_items = self.db.query(CartItem).filter(CartItem.cart_id == cart.id).all()
        
        offers = {}
        products = {}
        inventories = {}
        cart_total = Decimal('0')
        
        for item in cart_items:
            offer = self.db.query(Offer).filter(Offer.id == item.offer_id).first()
            if offer:
                offers[offer.id] = offer
                prod = self.db.query(Product).filter(Product.id == offer.product_id).first()
                inv = self.db.query(Inventory).filter(Inventory.offer_id == offer.id).first()
                if prod:
                    products[prod.id] = prod
                if inv:
                    inventories[inv.offer_id] = inv
            cart_total += item.unit_price * item.quantity
            
        approved_consent = self.db.query(ConsentRequest).filter(
            ConsentRequest.cart_id == cart.id,
            ConsentRequest.status == "APPROVED",
            ConsentRequest.amount == cart_total
        ).first()

        from app.models.user import UserSpendingLimit
        spending_limit = self.db.query(UserSpendingLimit).filter(UserSpendingLimit.user_id == customer.user_id).first() if hasattr(customer, 'user_id') else None
        
        context = {
            "merchant": merchant,
            "customer": customer,
            "cart": cart,
            "cart_items": cart_items,
            "merchant_rules": merchant_rules,
            "offers": offers,
            "products": products,
            "inventories": inventories,
            "cart_total": cart_total,
            "has_approved_consent": approved_consent is not None,
            "spending_limit": spending_limit
        }
        
        return self.evaluator.evaluate(context)

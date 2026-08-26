from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Dict, Any
from app.tools.base import CommerceTool, ToolError
from app.tools.multi_source_schemas import (
    SearchSourceCatalogInput,
    GetProductDetailsInput,
    CheckProductAvailabilityInput,
    GetMerchantPromotionInput,
    CompareProductsInput,
    RankProductsInput,
    CreateCheckoutSessionInput
)
from app.models.product import Product, Inventory
from app.models.promotion import Promotion
from app.models.order import Cart, CartItem
from app.services.core import CoreService

def _search_source(db_session: Session, source: str, query: str = None, category: str = None, max_price: float = None, limit: int = 10):
    stmt = select(Product).where(Product.source == source, Product.is_active == True)
    
    if query:
        stmt = stmt.where(Product.name.ilike(f"%{query}%"))
    if category:
        stmt = stmt.where(Product.category.ilike(f"%{category}%"))
    if max_price:
        stmt = stmt.where(Product.price <= max_price)
        
    products = db_session.scalars(stmt).all()
    
    results = []
    for p in products[:limit]:
        results.append({
            "id": str(p.id),
            "source": p.source,
            "name": p.name,
            "category": p.category,
            "price": float(p.price),
            "mrp": float(p.mrp) if p.mrp else None,
            "image_url": p.image_url,
            "rating": float(p.rating) if p.rating else None,
            "review_count": p.review_count,
            "delivery_estimate": p.delivery_estimate,
            "is_sponsored": p.is_sponsored
        })
    return {"products": results, "source": source, "count": len(results)}

class SearchAmazonCatalogTool(CommerceTool):
    name = "search_amazon_catalog"
    description = "Search the Amazon product catalog using structured criteria."
    input_schema = SearchSourceCatalogInput
    
    def execute(self, db_session: Session, **kwargs):
        return _search_source(
            db_session, 
            source="amazon", 
            query=kwargs.get("query"),
            category=kwargs.get("category"),
            max_price=float(kwargs.get("max_price")) if kwargs.get("max_price") else None,
            limit=kwargs.get("limit", 10)
        )

class SearchFlipkartCatalogTool(CommerceTool):
    name = "search_flipkart_catalog"
    description = "Search the Flipkart product catalog using structured criteria."
    input_schema = SearchSourceCatalogInput
    
    def execute(self, db_session: Session, **kwargs):
        return _search_source(
            db_session, 
            source="flipkart", 
            query=kwargs.get("query"),
            category=kwargs.get("category"),
            max_price=float(kwargs.get("max_price")) if kwargs.get("max_price") else None,
            limit=kwargs.get("limit", 10)
        )

class SearchRazorpayMerchantsTool(CommerceTool):
    name = "search_razorpay_merchants"
    description = "Search across Razorpay-connected merchant catalogs."
    input_schema = SearchSourceCatalogInput
    
    def execute(self, db_session: Session, **kwargs):
        return _search_source(
            db_session, 
            source="razorpay", 
            query=kwargs.get("query"),
            category=kwargs.get("category"),
            max_price=float(kwargs.get("max_price")) if kwargs.get("max_price") else None,
            limit=kwargs.get("limit", 10)
        )

class GetProductDetailsTool(CommerceTool):
    name = "get_product_details"
    description = "Get detailed information about a specific product."
    input_schema = GetProductDetailsInput
    
    def execute(self, db_session: Session, **kwargs):
        product_id = kwargs.get("product_id")
        p = db_session.get(Product, product_id)
        if not p:
            raise ToolError("PRODUCT_NOT_FOUND", "Product does not exist.")
            
        return {
            "id": str(p.id),
            "source": p.source,
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "brand": p.brand,
            "price": float(p.price),
            "rating": float(p.rating) if p.rating else None,
            "review_count": p.review_count,
            "delivery_estimate": p.delivery_estimate,
            "is_sponsored": p.is_sponsored,
            "product_url": p.product_url
        }

class CheckProductAvailabilityTool(CommerceTool):
    name = "check_product_availability"
    description = "Check if a product is in stock and available for delivery."
    input_schema = CheckProductAvailabilityInput
    
    def execute(self, db_session: Session, **kwargs):
        product_id = kwargs.get("product_id")
        inv = db_session.scalars(select(Inventory).where(Inventory.product_id == product_id)).first()
        if not inv:
            return {"available": False, "stock": 0}
        
        available = (inv.quantity - inv.reserved_quantity) > 0
        return {"available": available, "stock": inv.quantity - inv.reserved_quantity}

class GetMerchantPromotionTool(CommerceTool):
    name = "get_merchant_promotion"
    description = "Check if there is an active promotion for a specific product."
    input_schema = GetMerchantPromotionInput
    
    def execute(self, db_session: Session, **kwargs):
        product_id = kwargs.get("product_id")
        promo = db_session.scalars(select(Promotion).where(Promotion.product_id == product_id, Promotion.status == "ACTIVE")).first()
        if not promo or promo.remaining_budget <= 0:
            return {"promoted": False}
            
        return {
            "promoted": True,
            "priority": promo.priority,
            "budget": float(promo.remaining_budget)
        }

class CompareProductsTool(CommerceTool):
    name = "compare_products"
    description = "Compare multiple products side-by-side on price, rating, and features."
    input_schema = CompareProductsInput
    
    def execute(self, db_session: Session, **kwargs):
        product_ids = kwargs.get("product_ids", [])
        products = db_session.scalars(select(Product).where(Product.id.in_(product_ids))).all()
        
        comparison = []
        for p in products:
            comparison.append({
                "id": str(p.id),
                "name": p.name,
                "price": float(p.price),
                "rating": float(p.rating) if p.rating else 0,
                "delivery": p.delivery_estimate
            })
        return {"comparison": comparison}

class RankProductsTool(CommerceTool):
    name = "rank_products"
    description = "Rank a list of products based on customer requirements, combining relevance, price, rating, and merchant promotions."
    input_schema = RankProductsInput
    
    def execute(self, db_session: Session, **kwargs):
        product_ids = kwargs.get("product_ids", [])
        reqs = kwargs.get("customer_requirements", "").lower()
        
        products = db_session.scalars(select(Product).where(Product.id.in_(product_ids))).all()
        
        ranked = []
        for p in products:
            score = 50 # Base score
            
            # Very simple heuristic scoring for the demo
            if p.rating:
                score += float(p.rating) * 5
                
            if "cheap" in reqs and p.price < 5000:
                score += 15
                
            if "tomorrow" in reqs and "Tomorrow" in (p.delivery_estimate or ""):
                score += 20
                
            # Promotion influence is bounded
            is_promoted = False
            if p.is_sponsored:
                is_promoted = True
                score += 10 # Bounded promotion bump
                
            ranked.append({
                "id": str(p.id),
                "name": p.name,
                "source": p.source,
                "score": score,
                "is_sponsored": is_promoted,
                "price": float(p.price),
                "mrp": float(p.mrp) if p.mrp else None,
                "image_url": p.image_url,
                "rating": float(p.rating) if p.rating else 0,
                "delivery_estimate": p.delivery_estimate
            })
            
        # Sort by score descending
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return {"ranked_products": ranked}

class CreateCheckoutSessionTool(CommerceTool):
    name = "create_checkout_session"
    description = "Initiate a checkout session for a product. This adds the product to the cart and triggers checkout."
    input_schema = CreateCheckoutSessionInput
    read_only = False
    
    def execute(self, db_session: Session, **kwargs):
        merchant_id = kwargs.get("merchant_id")
        customer_id = kwargs.get("customer_id")
        product_id = kwargs.get("product_id")
        quantity = kwargs.get("quantity", 1)
        
        p = db_session.get(Product, product_id)
        if not p:
            raise ToolError("PRODUCT_NOT_FOUND", "Product not found")
            
        # Get or create cart
        cart = db_session.scalars(select(Cart).where(Cart.customer_id == customer_id, Cart.status == "ACTIVE")).first()
        if not cart:
            cart = Cart(customer_id=customer_id, merchant_id=merchant_id, status="ACTIVE", currency="INR")
            db_session.add(cart)
            db_session.flush()
            
        # Add item
        item = CartItem(cart_id=cart.id, product_id=product_id, quantity=quantity, unit_price=p.price)
        db_session.add(item)
        db_session.flush()
        
        # We don't trigger the Razorpay order here since the UI handles it, but we return a signal that checkout is ready
        return {
            "checkout_ready": True,
            "cart_id": str(cart.id),
            "message": f"Product {p.name} added to cart and ready for checkout."
        }

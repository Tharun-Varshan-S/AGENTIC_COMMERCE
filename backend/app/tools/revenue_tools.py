from typing import Dict, Any, Type
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from app.tools.base import CommerceTool
from app.tools.schemas import GetRevenueRecommendationInput, SuggestUpsellInput
from app.revenue import RevenueEngine, RevenueRecommendationRequest
from app.db.session import SessionLocal

class GetRevenueRecommendationTool(CommerceTool):
    name: str = "get_revenue_recommendation"
    description: str = (
        "Get a deterministic, explainable revenue-growth recommendation for a customer. "
        "Evaluates cross-sell, upsell, or alternatives based on budget, inventory, margin, and product affinity."
    )
    input_schema: Type[BaseModel] = GetRevenueRecommendationInput

    def execute(self, db_session, **kwargs) -> Dict[str, Any]:
        req = RevenueRecommendationRequest(**kwargs)
        db: Session = db_session
        engine = RevenueEngine(db)
        response = engine.recommend(req)
        return response.model_dump(mode='json')

class SuggestUpsellTool(CommerceTool):
    name: str = "suggest_upsell"
    description: str = "Suggests upsell products based on margin threshold or category for a specific cart before checkout."
    input_schema: Type[BaseModel] = SuggestUpsellInput
    read_only: bool = False

    def execute(self, db_session: Session, **kwargs) -> Dict[str, Any]:
        from app.models.order import Cart, CartItem
        from app.models.offer import Offer
        from app.models.product import Product
        from app.models.agent import AgentDecision
        from sqlalchemy import select

        merchant_id = kwargs.get("merchant_id")
        customer_id = kwargs.get("customer_id")
        cart_id = kwargs.get("cart_id")

        cart = db_session.query(Cart).filter(Cart.id == cart_id).first()
        if not cart:
            return {"suggestions": []}

        # Get current product categories in cart
        cart_item_offer_ids = [item.offer_id for item in cart.items]
        cart_categories = []
        for item in cart.items:
            if item.offer and item.offer.product:
                cart_categories.append(item.offer.product.category)
        cart_categories = list(set(cart_categories))

        # Query candidates: active offers, not in cart, matching category, margin > 20% (proxy)
        query = select(Offer).join(Product).filter(
            Offer.merchant_id == merchant_id,
            Offer.is_active == True,
            Offer.id.notin_(cart_item_offer_ids)
        )
        if cart_categories:
            query = query.filter(Product.category.in_(cart_categories))

        candidates = db_session.scalars(query).all()
        
        suggestions = []
        for offer in candidates:
            # Calculate discount as a proxy for high margin
            margin_proxy = 0
            if offer.mrp and offer.mrp > 0:
                margin_proxy = (offer.mrp - offer.price) / offer.mrp
            
            # Suggest if margin > 20%
            if margin_proxy > 0.2:
                suggestions.append({
                    "id": str(offer.id),
                    "name": offer.product.name if offer.product else "Upsell Item",
                    "price": str(offer.price),
                    "reason": "High margin recommendation"
                })
                
                # Log suggestion
                decision = AgentDecision(
                    customer_id=customer_id,
                    merchant_id=merchant_id,
                    decision_type="upsell_suggestion",
                    decision_status="SUGGESTED",
                    recommended_product_id=offer.product_id,
                    reason="High margin recommendation"
                )
                db_session.add(decision)
                
                if len(suggestions) >= 3:
                    break
                    
        db_session.commit()
        return {"suggestions": suggestions}

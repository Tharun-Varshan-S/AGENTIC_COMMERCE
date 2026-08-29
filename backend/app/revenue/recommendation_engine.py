from decimal import Decimal
from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.customer import CustomerEvent
from app.revenue.scoring import ScoringEngine

class RecommendationEngine:
    MIN_RECOMMENDATION_SCORE = 0.55

    def __init__(self, db: Session):
        self.db = db
        self.scoring_engine = ScoringEngine(db)

    def _get_price(self, product: Product) -> Decimal:
        offer = next((o for o in product.offers if o.is_active), product.offers[0] if product.offers else None)
        return offer.price if offer else Decimal("0.0")

    def _get_inventory(self, product: Product) -> int:
        offer = next((o for o in product.offers if o.is_active), product.offers[0] if product.offers else None)
        return (offer.inventory.quantity - offer.inventory.reserved_quantity) if offer and offer.inventory else 0

    def determine_intervention(self, primary: Product, candidate: Product, customer_budget: Optional[Decimal]) -> str:
        primary_price = self._get_price(primary)
        candidate_price = self._get_price(candidate)
        
        # Check alternative first
        primary_qty = self._get_inventory(primary)
        if primary_qty <= 0:
            candidate_qty = self._get_inventory(candidate)
            if candidate.category == primary.category and candidate_qty > 0:
                if customer_budget and candidate_price > customer_budget:
                    return "NONE"
                return "ALTERNATIVE"
            return "NONE"

        # UPSELL
        if candidate.category == primary.category:
            if candidate_price > primary_price:
                if customer_budget and candidate_price > customer_budget:
                    return "NONE"
                return "UPSELL"
            return "NONE"

        # CROSS_SELL
        if candidate.category != primary.category:
            if customer_budget and (primary_price + candidate_price) > customer_budget:
                return "NONE"
            
            # Check affinity threshold
            affinity = self.scoring_engine._get_affinity(primary.category, candidate.category)
            if affinity >= 0.4:
                return "CROSS_SELL"

        return "NONE"

    def select_best_candidate(
        self, 
        primary: Product, 
        candidates: List[Product], 
        customer_budget: Optional[Decimal], 
        customer_history: List[CustomerEvent]
    ) -> Tuple[Optional[Product], str, float, Dict[str, Any]]:
        
        best_candidate = None
        best_score = -1.0
        best_intervention = "NONE"
        best_details = {}

        for candidate in candidates:
            intervention = self.determine_intervention(primary, candidate, customer_budget)
            if intervention == "NONE":
                continue

            details = self.scoring_engine.score_candidate(primary, candidate, customer_budget, customer_history)
            
            # Budget explicitly checked in determine_intervention, but pass a flag for explainability
            primary_price = self._get_price(primary)
            candidate_price = self._get_price(candidate)
            if intervention in ["UPSELL", "ALTERNATIVE"]:
                details["budget_compatibility"] = customer_budget is not None and (candidate_price <= customer_budget)
            else:
                details["budget_compatibility"] = customer_budget is not None and (primary_price + candidate_price <= customer_budget)
            
            score = details["score"]
            if score >= self.MIN_RECOMMENDATION_SCORE and score > best_score:
                best_score = score
                best_candidate = candidate
                best_intervention = intervention
                best_details = details

        if best_candidate is None:
            return None, "NONE", 0.0, {}

        return best_candidate, best_intervention, best_score, best_details

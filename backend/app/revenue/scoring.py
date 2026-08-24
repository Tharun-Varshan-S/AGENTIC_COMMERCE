from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.product import Product
from app.models.customer import CustomerEvent

class ScoringEngine:
    def __init__(self, db: Session):
        self.db = db
        # Deterministic product affinity matrix
        self.affinity_map = {
            ("Gaming", "Accessories"): 0.91,
            ("Gaming", "Gaming"): 1.0,
            ("Gaming", "Audio"): 0.68,
            ("Gaming", "Streaming"): 0.45,
            ("Accessories", "Gaming"): 0.91,
            ("Accessories", "Audio"): 0.70,
            ("Audio", "Gaming"): 0.68,
            ("Streaming", "Gaming"): 0.45,
            ("Audio", "Accessories"): 0.70,
            ("Accessories", "Streaming"): 0.50
        }

    def _get_affinity(self, cat1: str, cat2: str) -> float:
        if cat1 == cat2:
            return 1.0
        return self.affinity_map.get((cat1, cat2), self.affinity_map.get((cat2, cat1), 0.31))

    def _get_purchase_probability(self, primary: Product, candidate: Product, customer_budget: Decimal, customer_history: List[CustomerEvent]) -> float:
        prob = 0.40 # base
        
        if primary.category == candidate.category:
            prob += 0.20
            
        recently_viewed_ids = [e.product_id for e in customer_history if e.event_type == 'VIEW']
        if candidate.id in recently_viewed_ids:
            prob += 0.20
            
        if primary.brand and candidate.brand and primary.brand == candidate.brand:
            prob += 0.05
            
        total_cost = primary.price + candidate.price
        if customer_budget and total_cost <= customer_budget:
            prob += 0.10
            
        return min(max(prob, 0.0), 1.0)

    def _get_margin_score(self, candidate: Product) -> float:
        if not candidate.cost_price or candidate.price <= 0:
            return 0.5 # fallback

        margin = float((candidate.price - candidate.cost_price) / candidate.price)
        # Normalize: 0% -> 0, 50% -> 1.0
        normalized = margin / 0.50
        return min(max(normalized, 0.0), 1.0)

    def _get_inventory_health_score(self, candidate: Product) -> float:
        qty = (candidate.inventory.quantity - candidate.inventory.reserved_quantity) if candidate.inventory else 0
        if qty <= 0:
            return 0.0
        elif 1 <= qty <= 5:
            return 0.3
        elif 6 <= qty <= 20:
            return 0.7
        else:
            return 1.0

    def _get_customer_preference_score(self, candidate: Product, customer_history: List[CustomerEvent]) -> float:
        score = 0.0
        for event in customer_history:
            if event.product_id == candidate.id:
                if event.event_type == 'VIEW':
                    score += 0.4
                elif event.event_type == 'PURCHASE':
                    score += 0.3
            if event.product and event.product.category == candidate.category:
                score += 0.3
                
        return min(max(score, 0.0), 1.0)

    def score_candidate(self, primary: Product, candidate: Product, customer_budget: Decimal, customer_history: List[CustomerEvent]) -> Dict[str, Any]:
        purchase_prob = self._get_purchase_probability(primary, candidate, customer_budget, customer_history)
        affinity = self._get_affinity(primary.category, candidate.category)
        margin = self._get_margin_score(candidate)
        inventory = self._get_inventory_health_score(candidate)
        pref = self._get_customer_preference_score(candidate, customer_history)

        # Apply component weights
        final_score = (
            0.35 * purchase_prob +
            0.25 * affinity +
            0.20 * margin +
            0.10 * inventory +
            0.10 * pref
        )

        return {
            "score": round(final_score, 4),
            "purchase_probability": round(purchase_prob, 4),
            "product_affinity": round(affinity, 4),
            "margin_score": round(margin, 4),
            "inventory_health": round(inventory, 4),
            "customer_preference": round(pref, 4)
        }

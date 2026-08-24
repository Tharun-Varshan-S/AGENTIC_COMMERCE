from typing import List, Dict, Any
from app.revenue.schemas import ExplanationFactor

class ExplainabilityEngine:
    def generate_explanation(self, details: Dict[str, Any], intervention: str) -> tuple[str, List[ExplanationFactor]]:
        if intervention == "NONE":
            return "No suitable recommendation satisfies current inventory and customer constraints", []

        factors = []
        reason_parts = []

        if details["product_affinity"] >= 0.7:
            factors.append(ExplanationFactor(
                name="product_affinity", 
                score=details["product_affinity"], 
                explanation="Highly complementary product category"
            ))
            reason_parts.append("High product affinity")
        elif details["product_affinity"] >= 0.4:
            factors.append(ExplanationFactor(
                name="product_affinity", 
                score=details["product_affinity"], 
                explanation="Related product category"
            ))

        if details["inventory_health"] >= 0.7:
            factors.append(ExplanationFactor(
                name="inventory_health", 
                score=details["inventory_health"], 
                explanation="Healthy inventory available"
            ))
            reason_parts.append("strong inventory availability")

        if details["purchase_probability"] >= 0.5: # indicating some strong matching (like budget/recently viewed)
            factors.append(ExplanationFactor(
                name="purchase_probability", 
                score=details["purchase_probability"], 
                explanation="Matches customer intent and constraints"
            ))
            reason_parts.append("fits customer intent")

        if details.get("budget_compatibility", False):
            factors.append(ExplanationFactor(
                name="budget_compatibility",
                score=1.0,
                explanation="Total remains within stated budget"
            ))
            reason_parts.append("within budget constraints")

        reason = ", ".join(reason_parts)
        if not reason:
            reason = "Recommended based on overall scoring metrics"
        else:
            reason = "Recommended due to: " + reason

        return reason, factors

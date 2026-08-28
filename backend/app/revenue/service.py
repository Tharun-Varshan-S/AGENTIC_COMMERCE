from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.product import Product
from app.models.customer import CustomerEvent
from app.models.agent import AgentDecision

from app.revenue.schemas import RevenueRecommendationRequest, RevenueRecommendationResponse, ProductSummary
from app.revenue.candidate_generator import CandidateGenerator
from app.revenue.recommendation_engine import RecommendationEngine
from app.revenue.explainability import ExplainabilityEngine

class RevenueEngine:
    def __init__(self, db: Session):
        self.db = db
        self.candidate_generator = CandidateGenerator(db)
        self.recommendation_engine = RecommendationEngine(db)
        self.explainability_engine = ExplainabilityEngine()

    def recommend(self, request: RevenueRecommendationRequest) -> RevenueRecommendationResponse:
        primary_product = self.db.scalars(
            select(Product).filter(
                Product.id == request.primary_product_id,
                Product.merchant_id == request.merchant_id
            )
        ).first()

        if not primary_product:
            raise ValueError("Primary product not found or belongs to a different merchant.")

        customer_history = self.db.scalars(
            select(CustomerEvent).filter(CustomerEvent.customer_id == request.customer_id)
        ).all()

        candidates = self.candidate_generator.generate(
            str(request.merchant_id),
            str(request.customer_id),
            primary_product
        )

        recommended, intervention, score, details = self.recommendation_engine.select_best_candidate(
            primary_product,
            candidates,
            request.customer_budget,
            customer_history
        )

        reason, factors = self.explainability_engine.generate_explanation(details, intervention)

        # Get active offer price for primary product
        primary_offer = next((o for o in primary_product.offers if o.is_active), primary_product.offers[0] if primary_product.offers else None)
        primary_price = primary_offer.price if primary_offer else Decimal("0.0")

        expected_order_value = primary_price
        additional_revenue = Decimal("0.0")
        if recommended:
            rec_offer = next((o for o in recommended.offers if o.is_active), recommended.offers[0] if recommended.offers else None)
            rec_price = rec_offer.price if rec_offer else Decimal("0.0")
            
            if intervention in ["UPSELL", "ALTERNATIVE"]:
                expected_order_value = rec_price
                additional_revenue = max(Decimal("0.0"), rec_price - primary_price)
            else:
                expected_order_value += rec_price
                additional_revenue = rec_price

        decision = AgentDecision(
            merchant_id=request.merchant_id,
            customer_id=request.customer_id,
            intent=request.customer_intent,
            primary_product_id=primary_product.id,
            intervention_type=intervention,
            recommended_product_id=recommended.id if recommended else None,
            reason=reason,
            score=score,
            scoring_details=details,
            expected_order_value=expected_order_value
        )
        self.db.add(decision)
        self.db.commit()

        return RevenueRecommendationResponse(
            primary_product=ProductSummary(
                id=primary_product.id,
                name=primary_product.name,
                price=primary_price
            ),
            intervention=intervention,
            recommended_product=ProductSummary(
                id=recommended.id,
                name=recommended.name,
                price=rec_price
            ) if recommended else None,
            reason=reason,
            score=score,
            expected_order_value=expected_order_value,
            additional_revenue=additional_revenue,
            factors=factors
        )

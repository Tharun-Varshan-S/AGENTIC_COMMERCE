from sqlalchemy.orm import Session
from sqlalchemy import select
from app.tools.base import CommerceTool, ToolError
from app.tools.schemas import GetRecommendationsInput
from app.models.agent import AgentDecision
from app.services.core import CoreService

class GetRecommendationsTool(CommerceTool):
    name = "get_recommendations"
    description = "Retrieve past static recommendations for a customer."
    input_schema = GetRecommendationsInput
    read_only = True

    def execute(self, db_session: Session, **kwargs):
        merchant_id = kwargs.get("merchant_id")
        customer_id = kwargs.get("customer_id")
        product_id = kwargs.get("product_id")

        query = select(AgentDecision).filter(
            AgentDecision.merchant_id == merchant_id,
            AgentDecision.customer_id == customer_id,
            AgentDecision.intervention_type.in_(["UPSELL", "CROSS_SELL", "ALTERNATIVE"])
        )

        if product_id:
            query = query.filter(AgentDecision.primary_product_id == product_id)

        decisions = db_session.scalars(query.order_by(AgentDecision.created_at.desc()).limit(5)).all()

        recommendations = []
        for d in decisions:
            primary_name = d.primary_product.name if d.primary_product else None
            recommended_name = d.recommended_product.name if d.recommended_product else None

            if not primary_name or not recommended_name:
                continue

            recommendations.append({
                "intervention_type": d.intervention_type,
                "primary_product": primary_name,
                "recommended_product": recommended_name,
                "reason": d.reason,
                "expected_order_value": float(d.expected_order_value) if d.expected_order_value else None
            })

        return {
            "recommendations": recommendations
        }

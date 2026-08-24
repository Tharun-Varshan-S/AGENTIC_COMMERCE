from typing import Dict, Any, Type
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json

from app.tools.base import CommerceTool
from app.tools.schemas import GetRevenueRecommendationInput
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

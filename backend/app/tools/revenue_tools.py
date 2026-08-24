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

    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        req = RevenueRecommendationRequest(**params)
        
        db: Session = SessionLocal()
        try:
            engine = RevenueEngine(db)
            response = engine.recommend(req)
            return response.model_dump(mode='json')
        except Exception as e:
            return {"error": str(e)}
        finally:
            db.close()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.revenue import RevenueEngine, RevenueRecommendationRequest, RevenueRecommendationResponse

router = APIRouter(prefix="/revenue", tags=["Revenue Intelligence"])

from app.api.auth import get_current_customer_user, verify_customer_ownership
from app.models.user import User

@router.post("/recommend", response_model=RevenueRecommendationResponse)
def get_revenue_recommendation(request: RevenueRecommendationRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    verify_customer_ownership(db, str(request.customer_id), current_user)
    try:
        engine = RevenueEngine(db)
        return engine.recommend(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while generating a recommendation.")

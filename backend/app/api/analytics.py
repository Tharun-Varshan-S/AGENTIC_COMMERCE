from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.analytics import AnalyticsService
from app.schemas.analytics import DashboardData, RecentActivity
from app.models.merchant import Merchant
from sqlalchemy import select

router = APIRouter(prefix="/analytics", tags=["Analytics"])

def get_demo_merchant(db: Session) -> Merchant:
    # For hackathon MVP, we use the first active merchant as context
    merchant = db.scalars(select(Merchant).filter(Merchant.is_active == True)).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="No active merchant found")
    return merchant

@router.get("/dashboard", response_model=DashboardData)
def get_dashboard(db: Session = Depends(get_db)):
    merchant = get_demo_merchant(db)
    service = AnalyticsService(db)
    return service.get_dashboard_data(str(merchant.id))

@router.get("/recent-activity", response_model=RecentActivity)
def get_recent_activity(db: Session = Depends(get_db)):
    merchant = get_demo_merchant(db)
    service = AnalyticsService(db)
    return service.get_recent_activity(str(merchant.id))

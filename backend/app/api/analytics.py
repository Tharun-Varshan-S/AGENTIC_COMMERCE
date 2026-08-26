from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.analytics import AnalyticsService
from app.schemas.analytics import DashboardData, RecentActivity
from app.models.merchant import Merchant
from app.models.product import Product
from sqlalchemy import select

router = APIRouter(prefix="/analytics", tags=["Analytics"])

from app.api.auth import get_current_merchant_user
@router.get("/dashboard", response_model=DashboardData)
def get_dashboard(db: Session = Depends(get_db), merchant: Merchant = Depends(get_current_merchant_user)):
    service = AnalyticsService(db)
    return service.get_dashboard_data(str(merchant.id))

@router.get("/recent-activity", response_model=RecentActivity)
def get_recent_activity(db: Session = Depends(get_db), merchant: Merchant = Depends(get_current_merchant_user)):
    service = AnalyticsService(db)
    return service.get_recent_activity(str(merchant.id))

from app.models.promotion import Promotion

@router.get("/activity-feed")
def get_activity_feed(db: Session = Depends(get_db), merchant: Merchant = Depends(get_current_merchant_user)):
    service = AnalyticsService(db)
    return service.get_activity_feed(str(merchant.id))

@router.get("/promotions")
def get_promotions(db: Session = Depends(get_db), merchant: Merchant = Depends(get_current_merchant_user)):
    # Return promotions with product details
    promos = db.scalars(select(Promotion).where(Promotion.merchant_id == merchant.id).order_by(Promotion.priority.desc())).all()
    results = []
    for p in promos:
        product = db.get(Product, p.product_id)
        results.append({
            "id": str(p.id),
            "product_name": product.name if product else "Unknown",
            "budget": float(p.budget),
            "remaining_budget": float(p.remaining_budget),
            "impressions": p.impressions,
            "clicks": p.clicks,
            "conversions": p.conversions,
            "status": p.status,
            "priority": p.priority
        })
    return results

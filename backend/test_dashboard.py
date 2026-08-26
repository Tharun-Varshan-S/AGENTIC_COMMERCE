from app.db.session import SessionLocal
from app.api.auth import get_demo_merchant
from app.services.analytics import AnalyticsService
db = SessionLocal()
try:
    merchant = get_demo_merchant(db)
    service = AnalyticsService(db)
    service.get_dashboard_data(str(merchant.id))
    print("Success")
except Exception as e:
    import traceback
    traceback.print_exc()

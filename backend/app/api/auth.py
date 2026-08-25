from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.merchant import Merchant

def get_demo_merchant(db: Session) -> Merchant:
    # For hackathon MVP, we use the first active merchant as context
    merchant = db.scalars(select(Merchant).filter(Merchant.is_active == True)).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="No active merchant found")
    return merchant

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.customer import Customer
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter()

class CustomerSettingsUpdate(BaseModel):
    transaction_limit: float | None = None
    daily_limit: float | None = None

class CustomerSettingsResponse(BaseModel):
    transaction_limit: float
    daily_limit: float
    spending_limit_set: bool  # True only if the user has explicitly configured a limit

@router.get("/settings", response_model=CustomerSettingsResponse)
def get_customer_settings(
    merchant_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    customer = db.scalars(select(Customer).filter(
        Customer.email == current_user.email,
        Customer.merchant_id == merchant_id
    )).first()

    if not customer or customer.transaction_limit is None:
        # No customer record or NULL limit → limit not configured
        return {
            "transaction_limit": 10000.0,
            "daily_limit": 50000.0,
            "spending_limit_set": False
        }

    return {
        "transaction_limit": float(customer.transaction_limit),
        "daily_limit": float(customer.daily_limit) if customer.daily_limit is not None else 50000.0,
        "spending_limit_set": True
    }

@router.put("/settings", response_model=CustomerSettingsResponse)
def update_customer_settings(
    merchant_id: str,
    settings: CustomerSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    from app.api.auth import resolve_customer
    customer = resolve_customer(db, current_user, merchant_id)

    if settings.transaction_limit is not None:
        customer.transaction_limit = settings.transaction_limit
    if settings.daily_limit is not None:
        customer.daily_limit = settings.daily_limit

    db.commit()
    db.refresh(customer)

    return {
        "transaction_limit": float(customer.transaction_limit) if customer.transaction_limit is not None else 10000.0,
        "daily_limit": float(customer.daily_limit) if customer.daily_limit is not None else 50000.0,
        "spending_limit_set": customer.transaction_limit is not None
    }

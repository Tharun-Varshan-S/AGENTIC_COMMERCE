from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal

from app.db.session import get_db
from app.services.core import CoreService
from app.schemas.core import (
    MerchantResponse,
    ProductResponse,
    InventoryResponse,
    CustomerResponse,
    MerchantRuleResponse
)

router = APIRouter()

def get_service(db: Session = Depends(get_db)) -> CoreService:
    return CoreService(db)

@router.get("/merchants", response_model=List[MerchantResponse])
def get_merchants(service: CoreService = Depends(get_service)):
    return service.get_merchants()

@router.get("/products", response_model=List[ProductResponse])
def get_products(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    max_price: Optional[Decimal] = None,
    service: CoreService = Depends(get_service)
):
    return service.get_products(category=category, is_active=is_active, search=search, max_price=max_price)

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID, service: CoreService = Depends(get_service)):
    product = service.get_product(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/inventory", response_model=List[InventoryResponse])
def get_inventory(service: CoreService = Depends(get_service)):
    return service.get_inventory()

@router.get("/customers", response_model=List[CustomerResponse])
def get_customers(service: CoreService = Depends(get_service)):
    return service.get_customers()

@router.get("/merchant-rules", response_model=List[MerchantRuleResponse])
def get_merchant_rules(merchant_id: UUID, service: CoreService = Depends(get_service)):
    return service.get_merchant_rules(merchant_id)

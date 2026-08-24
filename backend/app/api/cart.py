from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.db.session import get_db
from app.services.cart import CartService
from app.schemas.cart import CartResponse, CartCreate, CartItemCreate, CartItemUpdate

router = APIRouter()

def get_service(db: Session = Depends(get_db)) -> CartService:
    return CartService(db)

@router.get("/carts/active", response_model=CartResponse)
def get_active_cart(
    customer_id: UUID,
    service: CartService = Depends(get_service)
):
    cart = service.get_active_cart(customer_id)
    if not cart:
        raise HTTPException(status_code=404, detail="No active cart found")
    return cart

@router.post("/carts", response_model=CartResponse)
def create_cart(
    cart_in: CartCreate,
    service: CartService = Depends(get_service)
):
    return service.create_cart(cart_in.customer_id, cart_in.merchant_id)

@router.post("/carts/{cart_id}/items", response_model=CartResponse)
def add_cart_item(
    cart_id: UUID,
    item_in: CartItemCreate,
    service: CartService = Depends(get_service)
):
    return service.add_item_to_cart(cart_id, item_in.product_id, item_in.quantity)

@router.patch("/carts/{cart_id}/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    cart_id: UUID,
    item_id: UUID,
    item_in: CartItemUpdate,
    service: CartService = Depends(get_service)
):
    return service.update_item_quantity(cart_id, item_id, item_in.quantity)

@router.delete("/carts/{cart_id}/items/{item_id}", response_model=CartResponse)
def remove_cart_item(
    cart_id: UUID,
    item_id: UUID,
    service: CartService = Depends(get_service)
):
    return service.remove_item(cart_id, item_id)

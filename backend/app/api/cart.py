from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from app.db.session import get_db
from app.services.cart import CartService
from app.schemas.cart import CartResponse, CartCreate, CartItemCreate, CartItemUpdate
from app.api.auth import get_current_customer_user, verify_customer_ownership, resolve_customer
from app.models.user import User
from app.models.order import Cart

router = APIRouter()

def get_service(db: Session = Depends(get_db)) -> CartService:
    return CartService(db)

@router.get("/carts/active", response_model=CartResponse)
def get_active_cart(
    merchant_id: UUID,
    customer_id: Optional[UUID] = None,
    service: CartService = Depends(get_service),
    current_user: User = Depends(get_current_customer_user)
):
    customer = resolve_customer(service.db, current_user, str(merchant_id), str(customer_id) if customer_id else None)
    cart = service.get_active_cart(customer.id)
    if not cart:
        raise HTTPException(status_code=404, detail="No active cart found")
    return cart

@router.post("/carts", response_model=CartResponse)
def create_cart(
    cart_in: CartCreate,
    service: CartService = Depends(get_service),
    current_user: User = Depends(get_current_customer_user)
):
    customer = resolve_customer(service.db, current_user, str(cart_in.merchant_id), str(cart_in.customer_id) if cart_in.customer_id else None)
    return service.create_cart(customer.id, cart_in.merchant_id)

@router.post("/carts/{cart_id}/items", response_model=CartResponse)
def add_cart_item(
    cart_id: UUID,
    item_in: CartItemCreate,
    service: CartService = Depends(get_service),
    current_user: User = Depends(get_current_customer_user)
):
    cart = service.db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    verify_customer_ownership(service.db, str(cart.customer_id), current_user)
    return service.add_item_to_cart(cart_id, item_in.product_id, item_in.quantity, item_in.offer_id)

@router.patch("/carts/{cart_id}/items/{item_id}", response_model=CartResponse)
def update_cart_item(
    cart_id: UUID,
    item_id: UUID,
    item_in: CartItemUpdate,
    service: CartService = Depends(get_service),
    current_user: User = Depends(get_current_customer_user)
):
    cart = service.db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    verify_customer_ownership(service.db, str(cart.customer_id), current_user)
    return service.update_item_quantity(cart_id, item_id, item_in.quantity)

@router.delete("/carts/{cart_id}/items/{item_id}", response_model=CartResponse)
def remove_cart_item(
    cart_id: UUID,
    item_id: UUID,
    service: CartService = Depends(get_service),
    current_user: User = Depends(get_current_customer_user)
):
    cart = service.db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    verify_customer_ownership(service.db, str(cart.customer_id), current_user)
    return service.remove_item(cart_id, item_id)

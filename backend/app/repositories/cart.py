from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID
from datetime import datetime

from app.models.order import Cart, CartItem
from app.models.product import Product
from app.models.offer import Offer

class CartRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_cart(self, cart_id: UUID) -> Optional[Cart]:
        return self.db.get(Cart, cart_id)

    def get_active_cart(self, customer_id: UUID) -> Optional[Cart]:
        return self.db.scalars(
            select(Cart)
            .filter(Cart.customer_id == customer_id, Cart.status == "CHECKOUT")
        ).first()

    def create_cart(self, customer_id: UUID, merchant_id: UUID, currency: str = "INR") -> Cart:
        cart = Cart(
            customer_id=customer_id,
            merchant_id=merchant_id,
            status="CHECKOUT",
            currency=currency
        )
        self.db.add(cart)
        self.db.flush()
        return cart

    def get_cart_item(self, item_id: UUID) -> Optional[CartItem]:
        return self.db.get(CartItem, item_id)

    def get_cart_item_by_product(self, cart_id: UUID, product_id: UUID) -> Optional[CartItem]:
        """Find a CartItem in a cart for a given product (via Offer join)."""
        return self.db.scalars(
            select(CartItem)
            .join(Offer, CartItem.offer_id == Offer.id)
            .filter(CartItem.cart_id == cart_id, Offer.product_id == product_id)
        ).first()

    def add_item(self, cart_id: UUID, offer_id: UUID, quantity: int, unit_price: float) -> CartItem:
        """Add a CartItem using offer_id (CartItem links to Offer, not Product directly)."""
        item = CartItem(
            cart_id=cart_id,
            offer_id=offer_id,
            quantity=quantity,
            unit_price=unit_price
        )
        self.db.add(item)
        self.db.flush()
        
        # update cart updated_at
        cart = self.get_cart(cart_id)
        if cart:
            cart.updated_at = datetime.utcnow()
            
        return item

    def update_item_quantity(self, item: CartItem, quantity: int) -> CartItem:
        item.quantity = quantity
        self.db.flush()
        
        cart = self.get_cart(item.cart_id)
        if cart:
            cart.updated_at = datetime.utcnow()
            
        return item

    def remove_item(self, item: CartItem) -> None:
        cart_id = item.cart_id
        self.db.delete(item)
        self.db.flush()
        
        cart = self.get_cart(cart_id)
        if cart:
            cart.updated_at = datetime.utcnow()

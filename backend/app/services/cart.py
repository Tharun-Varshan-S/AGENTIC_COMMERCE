from typing import Optional, List
from sqlalchemy.orm import Session
from uuid import UUID
from fastapi import HTTPException
from decimal import Decimal

from app.repositories.cart import CartRepository
from app.repositories.core import CoreRepository
from app.schemas.cart import CartResponse, CartItemResponse, CartCreate
from app.schemas.core import ProductResponse

class CartService:
    def __init__(self, db: Session):
        self.repo = CartRepository(db)
        self.core_repo = CoreRepository(db)
        self.db = db

    def _build_cart_response(self, cart) -> CartResponse:
        items = []
        subtotal = Decimal("0")
        
        for item in cart.items:
            product = self.core_repo.get_product(item.product_id)
            if not product:
                continue
                
            unit_price = item.unit_price
            subtotal += (unit_price * item.quantity)
            
            # Get the best offer or default
            offer = None
            if hasattr(product, 'offers') and product.offers:
                offer = product.offers[0]
                
            prod_resp = ProductResponse(
                id=product.id,
                created_at=product.created_at,
                updated_at=product.updated_at,
                merchant_id=product.merchant_id,
                sku=product.sku,
                name=product.name,
                description=product.description,
                category=product.category,
                brand=product.brand,
                price=offer.price if offer else 0.0,
                cost_price=None,
                currency="INR",
                is_active=offer.is_active if offer else True,
                metadata_json=product.metadata_json,
                inventory=None
            )
            if product.inventory:
                prod_resp.inventory = {
                    "product_id": product.inventory.product_id,
                    "quantity": product.inventory.quantity,
                    "reserved_quantity": product.inventory.reserved_quantity,
                    "available_quantity": product.inventory.quantity - product.inventory.reserved_quantity
                }
                
            items.append(CartItemResponse(
                id=item.id,
                created_at=item.created_at,
                updated_at=item.updated_at,
                cart_id=item.cart_id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                product=prod_resp
            ))
            
        return CartResponse(
            id=cart.id,
            created_at=cart.created_at,
            updated_at=cart.updated_at,
            merchant_id=cart.merchant_id,
            customer_id=cart.customer_id,
            status=cart.status,
            currency=cart.currency,
            items=items,
            subtotal=subtotal
        )

    def get_active_cart(self, customer_id: UUID) -> Optional[CartResponse]:
        cart = self.repo.get_active_cart(customer_id)
        if not cart:
            return None
        return self._build_cart_response(cart)

    def create_cart(self, customer_id: UUID, merchant_id: UUID) -> CartResponse:
        cart = self.repo.get_active_cart(customer_id)
        if not cart:
            cart = self.repo.create_cart(customer_id, merchant_id)
            self.db.commit()
            self.db.refresh(cart)
        return self._build_cart_response(cart)

    def add_item_to_cart(self, cart_id: UUID, product_id: UUID, quantity: int) -> CartResponse:
        cart = self.repo.get_cart(cart_id)
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")
        if cart.status != "CHECKOUT":
            raise HTTPException(status_code=400, detail="Cart is not active")

        product = self.core_repo.get_product(product_id)
        if not product:
            raise HTTPException(status_code=400, detail="Product is unavailable")
            
        offer = None
        if hasattr(product, 'offers') and product.offers:
            active_offers = [o for o in product.offers if o.is_active]
            if active_offers:
                offer = active_offers[0]
                
        if not offer:
            raise HTTPException(status_code=400, detail="Product is unavailable")
            
        inventory = self.core_repo.get_inventory(product_id)
        available_quantity = 0
        if inventory:
            available_quantity = inventory.quantity - inventory.reserved_quantity
            
        item = self.repo.get_cart_item_by_product(cart_id, product_id)
        current_quantity = item.quantity if item else 0
        
        if current_quantity + quantity > available_quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Only {available_quantity} units are currently available."
            )

        if item:
            self.repo.update_item_quantity(item, current_quantity + quantity)
        else:
            self.repo.add_item(cart_id, product_id, quantity, offer.price)
            
        self.db.commit()
        self.db.refresh(cart)
        return self._build_cart_response(cart)

    def update_item_quantity(self, cart_id: UUID, item_id: UUID, quantity: int) -> CartResponse:
        cart = self.repo.get_cart(cart_id)
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        item = self.repo.get_cart_item(item_id)
        if not item or item.cart_id != cart_id:
            raise HTTPException(status_code=404, detail="Item not found in cart")

        if quantity <= 0:
            self.repo.remove_item(item)
        else:
            inventory = self.core_repo.get_inventory(item.product_id)
            available_quantity = 0
            if inventory:
                available_quantity = inventory.quantity - inventory.reserved_quantity
                
            if quantity > available_quantity:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Only {available_quantity} units are currently available."
                )
            
            self.repo.update_item_quantity(item, quantity)
            
        self.db.commit()
        self.db.refresh(cart)
        return self._build_cart_response(cart)

    def remove_item(self, cart_id: UUID, item_id: UUID) -> CartResponse:
        cart = self.repo.get_cart(cart_id)
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        item = self.repo.get_cart_item(item_id)
        if not item or item.cart_id != cart_id:
            raise HTTPException(status_code=404, detail="Item not found in cart")

        self.repo.remove_item(item)
        self.db.commit()
        self.db.refresh(cart)
        return self._build_cart_response(cart)

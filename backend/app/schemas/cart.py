from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from decimal import Decimal
from app.schemas.core import ORMBase, ProductResponse

class CartItemBase(BaseModel):
    product_id: UUID
    quantity: int

class CartItemCreate(CartItemBase):
    pass

class CartItemUpdate(BaseModel):
    quantity: int

class CartItemResponse(ORMBase):
    cart_id: UUID
    product_id: UUID
    quantity: int
    unit_price: Decimal
    product: Optional[ProductResponse] = None

class CartBase(BaseModel):
    customer_id: UUID

class CartCreate(CartBase):
    merchant_id: UUID

class CartResponse(ORMBase):
    merchant_id: UUID
    customer_id: UUID
    status: str
    currency: str
    items: List[CartItemResponse] = []
    subtotal: Decimal

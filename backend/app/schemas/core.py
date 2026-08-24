from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from decimal import Decimal

class ORMBase(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MerchantBase(BaseModel):
    name: str
    description: Optional[str] = None
    email: str
    currency: str = "INR"
    is_active: bool = True

class MerchantResponse(MerchantBase, ORMBase):
    pass

class MerchantRuleResponse(ORMBase):
    merchant_id: UUID
    max_transaction_amount: Optional[Decimal]
    max_discount_percent: Optional[Decimal]
    min_margin_percent: Optional[Decimal]
    auto_approval_limit: Optional[Decimal]
    require_consent: bool

class InventoryResponse(BaseModel):
    product_id: UUID
    quantity: int
    reserved_quantity: int
    available_quantity: int

class ProductBase(BaseModel):
    merchant_id: UUID
    sku: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    brand: Optional[str] = None
    price: Decimal
    cost_price: Optional[Decimal] = None
    currency: str = "INR"
    is_active: bool = True
    metadata_json: Optional[Dict[str, Any]] = None

class ProductResponse(ProductBase, ORMBase):
    inventory: Optional[InventoryResponse] = None

class CustomerBase(BaseModel):
    merchant_id: UUID
    external_reference: Optional[str] = None
    name: str
    email: Optional[str] = None
    budget_preference: Optional[str] = None

class CustomerResponse(CustomerBase, ORMBase):
    pass

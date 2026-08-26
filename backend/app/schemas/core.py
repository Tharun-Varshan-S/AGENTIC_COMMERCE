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
    source: str = "razorpay"
    rating: Optional[Decimal] = None
    review_count: int = 0
    delivery_estimate: Optional[str] = None
    is_sponsored: bool = False
    product_url: Optional[str] = None
    image_url: Optional[str] = None
    mrp: Optional[Decimal] = None
    metadata_json: Optional[Dict[str, Any]] = None

class PromotionBase(BaseModel):
    merchant_id: UUID
    product_id: UUID
    budget: Decimal
    remaining_budget: Decimal
    priority: int = 1
    status: str = "ACTIVE"
    target_category: Optional[str] = None
    target_keywords: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class PromotionResponse(PromotionBase, ORMBase):
    impressions: int = 0
    agent_recommendations: int = 0
    clicks: int = 0
    conversions: int = 0

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

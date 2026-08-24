from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

# Tool 1: search_catalog
class SearchCatalogInput(BaseModel):
    merchant_id: UUID
    query: Optional[str] = None
    category: Optional[str] = None
    max_price: Optional[Decimal] = None
    limit: Optional[int] = Field(default=10, le=50)

# Tool 2: get_product
class GetProductInput(BaseModel):
    merchant_id: UUID
    product_id: UUID

# Tool 3: check_inventory
class CheckInventoryInput(BaseModel):
    merchant_id: UUID
    product_id: UUID

# Tool 4: get_customer_context
class GetCustomerContextInput(BaseModel):
    merchant_id: UUID
    customer_id: UUID

# Tool 5: calculate_cart
class CalculateCartInput(BaseModel):
    merchant_id: UUID
    customer_id: UUID

# Tool 6: get_recommendations
class GetRecommendationsInput(BaseModel):
    merchant_id: UUID
    customer_id: UUID
    product_id: Optional[UUID] = None

# Tool 7: validate_cart
class ValidateCartInput(BaseModel):
    merchant_id: UUID
    customer_id: UUID

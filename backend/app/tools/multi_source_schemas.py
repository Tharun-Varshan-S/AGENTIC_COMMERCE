from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from decimal import Decimal

class SearchSourceCatalogInput(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    max_price: Optional[Decimal] = None
    limit: Optional[int] = Field(default=10, le=50)
    # The source is implicit in the tool itself (e.g. search_amazon_catalog)

class GetProductDetailsInput(BaseModel):
    source: str
    product_id: str # UUID or string

class CheckProductAvailabilityInput(BaseModel):
    source: str
    product_id: str

class GetMerchantPromotionInput(BaseModel):
    product_id: str

class CompareProductsInput(BaseModel):
    product_ids: List[str]

class RankProductsInput(BaseModel):
    product_ids: List[str]
    customer_requirements: str

class CreateCheckoutSessionInput(BaseModel):
    merchant_id: UUID
    customer_id: UUID
    product_id: str
    quantity: int = 1

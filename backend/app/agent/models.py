from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from pydantic import field_validator
import re

class ShoppingIntent(BaseModel):
    query: str = Field(description="Core product name or category")
    keywords: List[str] = Field(description="Search keywords")
    max_price: Optional[float] = Field(default=None, description="Maximum budget")
    min_price: Optional[float] = Field(default=None, description="Minimum budget")
    features: List[str] = Field(default=[], description="Specific required features (e.g., '256GB', 'wireless')")
    brand_preference: Optional[str] = Field(default=None, description="Preferred brand")
    is_search: bool = Field(description="Whether the user is actively searching for a product")

    @field_validator('query')
    @classmethod
    def sanitize_query(cls, v: str) -> str:
        # Strip arbitrary SQL/code injection characters
        sanitized = re.sub(r'[;\'\"\\=]', '', v)
        return sanitized

class NormalizedProduct(BaseModel):
    id: str
    offer_id: str
    merchant: str # "local_db", "amazon", "flipkart"
    title: str
    price: float
    description: str
    url: Optional[str] = None
    features: Dict[str, Any] = Field(default_factory=dict)
    relevance_score: Optional[float] = 0.0
    delivery_estimate: Optional[str] = None


from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ShoppingIntent(BaseModel):
    query: str = Field(description="Core product name or category")
    keywords: List[str] = Field(description="Search keywords")
    max_price: Optional[float] = Field(default=None, description="Maximum budget")
    min_price: Optional[float] = Field(default=None, description="Minimum budget")
    features: List[str] = Field(default_factory=list, description="Specific required features (e.g., '256GB', 'wireless')")
    brand_preference: Optional[str] = Field(default=None, description="Preferred brand")
    is_search: bool = Field(description="Whether the user is actively searching for a product")

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


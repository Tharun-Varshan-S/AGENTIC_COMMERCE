from abc import ABC, abstractmethod
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.product import Product
from app.models.offer import Offer
from app.agent.models import NormalizedProduct

class Merchant(ABC):
    """
    Abstract base class representing a UCP/ACP compatible merchant.
    This encapsulates the capabilities of discovery, catalog search, and checkout intent.
    """
    name: str
    base_url: str
    
    @abstractmethod
    def search_catalog(self, db_session: Session, query: str, category: Optional[str] = None, max_price: Optional[float] = None, limit: int = 10) -> List[NormalizedProduct]:
        """
        Search the merchant's catalog. In a full UCP implementation, this would hit an external A2A endpoint.
        Here we mock it by hitting our local product database partitioned by `source`.
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> dict:
        """
        Returns UCP capabilities (discovery).
        """
        pass


class BaseDBMerchant(Merchant):
    """
    A merchant that resolves products from our local SQL DB partitioned by 'source'.
    """
    source_id: str

    def search_catalog(self, db_session: Session, query: str, category: Optional[str] = None, max_price: Optional[float] = None, limit: int = 10) -> List[NormalizedProduct]:
        stmt = select(Offer).join(Product).where(Offer.source == self.source_id, Offer.is_active == True)
        
        if query:
            stmt = stmt.where(Product.name.ilike(f"%{query}%"))
        if category:
            stmt = stmt.where(Product.category.ilike(f"%{category}%"))
        if max_price:
            stmt = stmt.where(Offer.price <= max_price)
            
        offers = db_session.scalars(stmt).limit(limit).all()
        
        normalized = []
        for o in offers:
            normalized.append(
                NormalizedProduct(
                    id=str(o.product.id), # We still want the global product ID for agent tracking
                    offer_id=str(o.id), # Adding offer ID
                    merchant=self.source_id,
                    title=o.product.name,
                    price=float(o.price),
                    description=o.product.description or "",
                    in_stock=True, # Simple mock
                    url=o.product.product_url or f"https://{self.source_id}.com/offer/{o.id}",
                    delivery_estimate=o.delivery_estimate
                )
            )
        return normalized

    def get_capabilities(self) -> dict:
        return {
            "version": "1.0.0",
            "capabilities": {
                "checkout": [{"version": "1.0"}],
                "search": [{"version": "1.0"}]
            }
        }


class LocalRazorpayMerchant(BaseDBMerchant):
    name = "Razorpay Local"
    base_url = "https://razorpay.com/local"
    source_id = "razorpay"


class AmazonMerchant(BaseDBMerchant):
    name = "Amazon"
    base_url = "https://amazon.in"
    source_id = "amazon"


class FlipkartMerchant(BaseDBMerchant):
    name = "Flipkart"
    base_url = "https://flipkart.com"
    source_id = "flipkart"


def get_available_merchants() -> List[Merchant]:
    """
    Discovery function that returns all registered UCP merchants.
    """
    return [
        LocalRazorpayMerchant(),
        AmazonMerchant(),
        FlipkartMerchant()
    ]

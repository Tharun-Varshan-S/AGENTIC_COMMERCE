from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.product import Product
from app.models.offer import Offer
from app.models.customer import CustomerEvent

class CandidateGenerator:
    def __init__(self, db: Session):
        self.db = db

    def generate(self, merchant_id: str, customer_id: str, primary_product: Product) -> List[Product]:
        """
        Generate candidate products for recommendation.
        Returns products from the same merchant that are active and in stock.
        """
        # Fetch all active products for the merchant
        # For a hackathon/MVP, fetching all active products and filtering in memory is fine.
        # In a real app, this would be optimized.
        candidates_query = select(Product).join(Offer, Offer.product_id == Product.id).filter(
            Product.merchant_id == merchant_id,
            Offer.is_active == True,
            Product.id != primary_product.id
        )
        
        candidates = self.db.scalars(candidates_query).all()

        valid_candidates = []
        for candidate in candidates:
            # Find the active offer
            active_offer = next((o for o in candidate.offers if o.is_active), None)
            if not active_offer or not active_offer.inventory:
                continue
            
            # Basic eligibility filter
            if (active_offer.inventory.quantity - active_offer.inventory.reserved_quantity) <= 0:
                continue
            valid_candidates.append(candidate)

        return valid_candidates

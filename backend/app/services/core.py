from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
from decimal import Decimal

from app.repositories.core import CoreRepository
from app.schemas.core import (
    MerchantResponse,
    ProductResponse,
    InventoryResponse,
    CustomerResponse,
    MerchantRuleResponse
)

class CoreService:
    def __init__(self, db: Session):
        self.repo = CoreRepository(db)

    def get_merchants(self) -> List[MerchantResponse]:
        merchants = self.repo.get_merchants()
        return [MerchantResponse.model_validate(m) for m in merchants]

    def get_products(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        max_price: Optional[Decimal] = None,
        merchant_id: Optional[UUID] = None
    ) -> List[ProductResponse]:
        products = self.repo.get_products(
            category=category, 
            is_active=is_active, 
            search=search, 
            max_price=max_price, 
            merchant_id=merchant_id
        )
        
        results = []
        for p in products:
            offer = None
            if p.offers:
                active_offers = [o for o in p.offers if o.is_active]
                offer = active_offers[0] if active_offers else p.offers[0]
                
            prod_dict = {
                "id": p.id,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "merchant_id": p.merchant_id,
                "sku": p.sku,
                "name": p.name,
                "description": p.description,
                "category": p.category,
                "brand": p.brand,
                "price": offer.price if offer else Decimal("0.0"),
                "cost_price": None,
                "currency": offer.currency if offer else "INR",
                "is_active": offer.is_active if offer else True,
                "metadata_json": p.metadata_json,
                "inventory": None
            }
            if offer and offer.inventory:
                prod_dict["inventory"] = {
                    "product_id": p.id,
                    "quantity": offer.inventory.quantity,
                    "reserved_quantity": offer.inventory.reserved_quantity,
                    "available_quantity": offer.inventory.quantity - offer.inventory.reserved_quantity
                }
            results.append(ProductResponse(**prod_dict))
        return results

    def get_product(self, product_id: UUID) -> Optional[ProductResponse]:
        p = self.repo.get_product(product_id)
        if not p:
            return None
        
        offer = None
        if p.offers:
            active_offers = [o for o in p.offers if o.is_active]
            offer = active_offers[0] if active_offers else p.offers[0]
            
        prod_dict = {
            "id": p.id,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
            "merchant_id": p.merchant_id,
            "sku": p.sku,
            "name": p.name,
            "description": p.description,
            "category": p.category,
            "brand": p.brand,
            "price": offer.price if offer else Decimal("0.0"),
            "cost_price": None,
            "currency": offer.currency if offer else "INR",
            "is_active": offer.is_active if offer else True,
            "metadata_json": p.metadata_json,
            "inventory": None
        }
        if offer and offer.inventory:
            prod_dict["inventory"] = {
                "product_id": p.id,
                "quantity": offer.inventory.quantity,
                "reserved_quantity": offer.inventory.reserved_quantity,
                "available_quantity": offer.inventory.quantity - offer.inventory.reserved_quantity
            }
        return ProductResponse(**prod_dict)

    def get_inventory(self) -> List[InventoryResponse]:
        inventories = self.repo.get_all_inventory()
        return [
            InventoryResponse(
                product_id=inv.offer.product_id if inv.offer else inv.id,
                quantity=inv.quantity,
                reserved_quantity=inv.reserved_quantity,
                available_quantity=inv.quantity - inv.reserved_quantity
            ) for inv in inventories
        ]

    def get_customers(self, merchant_id: Optional[UUID] = None) -> List[CustomerResponse]:
        customers = self.repo.get_customers(merchant_id=merchant_id)
        return [CustomerResponse.model_validate(c) for c in customers]

    def get_merchant_rules(self, merchant_id: UUID) -> List[MerchantRuleResponse]:
        rules = self.repo.get_merchant_rules(merchant_id)
        return [MerchantRuleResponse.model_validate(r) for r in rules]

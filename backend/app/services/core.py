from typing import List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

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
        search: Optional[str] = None
    ) -> List[ProductResponse]:
        products = self.repo.get_products(category=category, is_active=is_active, search=search)
        
        results = []
        for p in products:
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
                "price": p.price,
                "cost_price": p.cost_price,
                "currency": p.currency,
                "is_active": p.is_active,
                "metadata_json": p.metadata_json,
                "inventory": None
            }
            if p.inventory:
                prod_dict["inventory"] = {
                    "product_id": p.inventory.product_id,
                    "quantity": p.inventory.quantity,
                    "reserved_quantity": p.inventory.reserved_quantity,
                    "available_quantity": p.inventory.quantity - p.inventory.reserved_quantity
                }
            results.append(ProductResponse(**prod_dict))
        return results

    def get_product(self, product_id: UUID) -> Optional[ProductResponse]:
        p = self.repo.get_product(product_id)
        if not p:
            return None
        
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
            "price": p.price,
            "cost_price": p.cost_price,
            "currency": p.currency,
            "is_active": p.is_active,
            "metadata_json": p.metadata_json,
            "inventory": None
        }
        if p.inventory:
            prod_dict["inventory"] = {
                "product_id": p.inventory.product_id,
                "quantity": p.inventory.quantity,
                "reserved_quantity": p.inventory.reserved_quantity,
                "available_quantity": p.inventory.quantity - p.inventory.reserved_quantity
            }
        return ProductResponse(**prod_dict)

    def get_inventory(self) -> List[InventoryResponse]:
        inventories = self.repo.get_all_inventory()
        return [
            InventoryResponse(
                product_id=inv.product_id,
                quantity=inv.quantity,
                reserved_quantity=inv.reserved_quantity,
                available_quantity=inv.quantity - inv.reserved_quantity
            ) for inv in inventories
        ]

    def get_customers(self) -> List[CustomerResponse]:
        customers = self.repo.get_customers()
        return [CustomerResponse.model_validate(c) for c in customers]

    def get_merchant_rules(self, merchant_id: UUID) -> List[MerchantRuleResponse]:
        rules = self.repo.get_merchant_rules(merchant_id)
        return [MerchantRuleResponse.model_validate(r) for r in rules]

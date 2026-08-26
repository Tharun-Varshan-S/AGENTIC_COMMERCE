from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_
from decimal import Decimal
from uuid import UUID

from app.models.merchant import Merchant, MerchantRule
from app.models.product import Product, Inventory
from app.models.customer import Customer

class CoreRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_merchants(self) -> List[Merchant]:
        return self.db.scalars(select(Merchant)).all()

    def get_products(
        self,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        max_price: Optional[Decimal] = None,
        merchant_id: Optional[UUID] = None
    ) -> List[Product]:
        query = select(Product)
        if merchant_id:
            query = query.filter(Product.merchant_id == merchant_id)
        if category:
            query = query.filter(Product.category == category)
        if is_active is not None:
            query = query.filter(Product.is_active == is_active)
        if search:
            search_term = f"%{search}%"
            query = query.filter(or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term),
                Product.sku.ilike(search_term)
            ))
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        return self.db.scalars(query).all()

    def get_product(self, product_id: UUID) -> Optional[Product]:
        return self.db.get(Product, product_id)

    def get_inventory(self, product_id: UUID) -> Optional[Inventory]:
        return self.db.scalar(select(Inventory).filter(Inventory.product_id == product_id))
    
    def get_all_inventory(self) -> List[Inventory]:
        return self.db.scalars(select(Inventory)).all()

    def get_customers(self) -> List[Customer]:
        return self.db.scalars(select(Customer)).all()

    def get_merchant_rules(self, merchant_id: UUID) -> List[MerchantRule]:
        return self.db.scalars(select(MerchantRule).filter(MerchantRule.merchant_id == merchant_id)).all()

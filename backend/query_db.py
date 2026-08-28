from app.db.session import SessionLocal
from app.models.product import Product
from app.models.offer import Offer

db = SessionLocal()
offers = db.query(Offer).join(Product).filter(Product.name.ilike('%G304%')).all()
for o in offers:
    print(f"Product: {o.product.name} (ID: {o.product.id})")
    print(f"Offer ID: {o.id}, Source: {o.source}, Price: {o.price}")
    print(f"Inventory: {o.inventory.quantity if o.inventory else 'None'}")
    print("---")

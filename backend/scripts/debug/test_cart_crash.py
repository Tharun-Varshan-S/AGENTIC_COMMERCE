import sys
import os
from uuid import UUID

sys.path.append('.')
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import engine, SessionLocal
from app.services.cart import CartService

db = SessionLocal()
try:
    cart_service = CartService(db)
    
    # Let's get the active cart for the demo customer
    from app.models.customer import Customer
    from app.models.product import Product, Offer
    
    # We will pick the first product and offer
    offer = db.query(Offer).first()
    product_id = offer.product_id
    offer_id = offer.id
    
    # get cart 
    cart_id = UUID("a9f21c42-f798-4d34-9a2b-44f6e59e074d")
    
    print("Testing add_item_to_cart...")
    result = cart_service.add_item_to_cart(cart_id, product_id, 1, offer_id)
    print("Success!", result.id)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()

import sys
import os
import requests

sys.path.append('.')
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import engine, SessionLocal
import app.db.base
from app.models.offer import Offer

db = SessionLocal()
try:
    offer = db.query(Offer).filter(Offer.is_active == True).first()
    offer_id = str(offer.id)
    product_id = str(offer.product_id)
    print("Found offer:", offer_id, "Product:", product_id)
    
    # Make request
    cart_id = "a9f21c42-f798-4d34-9a2b-44f6e59e074d"
    payload = {"product_id": product_id, "quantity": 1, "offer_id": offer_id}
    print("Sending payload:", payload)

    res = requests.post(f"http://localhost:8000/api/carts/{cart_id}/items", json=payload)
    print("Add item status:", res.status_code)
    print("Headers:", res.headers)
    print("Response:", res.text)
finally:
    db.close()

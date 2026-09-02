import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.user import User
from app.models.merchant import Merchant
from app.api.auth import resolve_customer

db = SessionLocal()
user = db.query(User).first()
merchant = db.query(Merchant).first()

if user and merchant:
    print(f"User: {user.email}, Merchant: {merchant.name}")
    try:
        customer = resolve_customer(db, user, str(merchant.id))
        print(f"Resolved customer: {customer.id}")
    except Exception as e:
        import traceback
        traceback.print_exc()
else:
    print("No user or merchant found")

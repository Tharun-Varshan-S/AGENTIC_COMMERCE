import httpx
import asyncio
import uuid
from decimal import Decimal
import os
import sys

sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.db.session import SessionLocal
import app.db.base
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.product import Product, Inventory
from app.models.offer import Offer
from app.models.user import User
from app.core.security import create_access_token, get_password_hash
from app.models.payment_authorization import AgenticPaymentAuthorization

API_URL = "http://localhost:8080"

async def setup():
    db = SessionLocal()
    m = Merchant(id=str(uuid.uuid4()), name="Audit Test Merchant", email=f"audit_{uuid.uuid4()}@merch.com", is_active=True)
    c = Customer(id=str(uuid.uuid4()), merchant_id=m.id, name="Audit Test Cust", email=f"audit_{uuid.uuid4()}@cust.com")
    u = User(id=str(uuid.uuid4()), email=c.email, hashed_password=get_password_hash("testpass"), role="CUSTOMER", full_name="Audit Test Cust")
    
    p_nice = Product(id=str(uuid.uuid4()), merchant_id=m.id, sku=f"SKU-NICE-{uuid.uuid4().hex[:6]}", name="Nice Watch", category="Accessories")
    o_nice = Offer(id=str(uuid.uuid4()), merchant_id=m.id, product_id=p_nice.id, price=Decimal('200.00'), mrp=Decimal('250.00'))
    Inventory(offer_id=o_nice.id, quantity=10)
    
    p_exp = Product(id=str(uuid.uuid4()), merchant_id=m.id, sku=f"SKU-EXP-{uuid.uuid4().hex[:6]}", name="Expensive TV", category="Electronics")
    o_exp = Offer(id=str(uuid.uuid4()), merchant_id=m.id, product_id=p_exp.id, price=Decimal('5000.00'), mrp=Decimal('5000.00'))
    Inventory(offer_id=o_exp.id, quantity=10)
    
    db.add_all([m, c, u, p_nice, o_nice, p_exp, o_exp])
    
    auth = AgenticPaymentAuthorization(
        id=str(uuid.uuid4()), customer_id=c.id, merchant_id=m.id, status="ACTIVE", rail="WALLET",
        provider="internal", per_transaction_limit=Decimal('2000.00'), daily_limit=Decimal('5000.00'), spent_today=Decimal('0.00')
    )
    db.add(auth)
    db.commit()
    
    return m.id, c.id, create_access_token({"sub": c.email})

def parse_stream(res):
    import json
    lines = res.text.strip().split('\n')
    for line in reversed(lines):
        if not line: continue
        try:
            obj = json.loads(line)
            if obj.get("type") == "final_result":
                return obj.get("data", {})
        except:
            pass
    return {}

async def run_tests():
    m_id, c_id, token = await setup()
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(timeout=120) as client:
        print("\n=== TEST 1: Explainable ===")
        res = await client.post(f"{API_URL}/api/agent/chat", headers=headers, json={
            "session_id": "test_1", "merchant_id": str(m_id), "customer_id": str(c_id),
            "message": "I want to buy the Nice Watch. Why did you pick this product?"
        })
        print(f"Agent: {parse_stream(res).get('message')}")
        
        print("\n=== TEST 2: Over spend limit ===")
        res = await client.post(f"{API_URL}/api/agent/chat", headers=headers, json={
            "session_id": "test_2", "merchant_id": str(m_id), "customer_id": str(c_id),
            "message": "I want to buy the Expensive TV."
        })
        print(f"Agent: {parse_stream(res).get('message')}")
        
        print("\n=== TEST 3: Unapproved merchant ===")
        res = await client.post(f"{API_URL}/api/agent/chat", headers=headers, json={
            "session_id": "test_3", "merchant_id": str(uuid.uuid4()), "customer_id": str(c_id),
            "message": "I want to buy a laptop."
        })
        print(f"Agent: {parse_stream(res).get('message', res.text)}")
        
        print("\n=== TEST 4: Ambiguous intent ===")
        res = await client.post(f"{API_URL}/api/agent/chat", headers=headers, json={
            "session_id": "test_4", "merchant_id": str(m_id), "customer_id": str(c_id),
            "message": "Buy me something nice."
        })
        print(f"Agent: {parse_stream(res).get('message')}")

if __name__ == "__main__":
    asyncio.run(run_tests())

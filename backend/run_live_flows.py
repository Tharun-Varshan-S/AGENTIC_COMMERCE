import httpx
import asyncio
import uuid
import time
from decimal import Decimal
import os
import sys

# We need SQLAlchemy models to verify DB state
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.db.session import SessionLocal
import app.db.base # imports all models
from app.models.merchant import Merchant, MerchantAPIKey
from app.models.customer import Customer
from app.models.product import Product, Inventory
from app.models.offer import Offer
from app.models.order import Cart, Order
from app.models.agent import AgentDecision
from app.models.payment_authorization import AgenticPaymentAuthorization
from app.models.audit import AuditLog
from app.models.promotion import Promotion

API_URL = "http://localhost:8080"

async def setup_data():
    db = SessionLocal()
    # Create merchant and customer
    m = Merchant(id=str(uuid.uuid4()), name="Live Test Merchant", email=f"live_{uuid.uuid4()}@merch.com", is_active=True)
    c = Customer(id=str(uuid.uuid4()), merchant_id=m.id, name="Live Test Cust", email=f"live_{uuid.uuid4()}@cust.com")
    
    from app.models.user import User
    from app.core.security import create_access_token, get_password_hash
    u = User(id=str(uuid.uuid4()), email=c.email, hashed_password=get_password_hash("testpass"), role="CUSTOMER", full_name="Live Test Cust")
    
    import hashlib
    # API Key for external agent (if needed)
    api_key_val = f"sk_test_{uuid.uuid4().hex}"
    api_key_hash = hashlib.sha256(api_key_val.encode()).hexdigest()
    api_key = MerchantAPIKey(id=str(uuid.uuid4()), merchant_id=m.id, key_hash=api_key_hash, is_active=True, name="Test Key")
    
    # Generate customer JWT
    cust_token = create_access_token({"sub": c.email})
    
    # Products
    # 1. Laptop (Normal)
    p_laptop = Product(id=str(uuid.uuid4()), merchant_id=m.id, sku=f"SKU-LAP-{uuid.uuid4().hex[:6]}", name="Test Laptop", category="Electronics")
    o_laptop = Offer(id=str(uuid.uuid4()), merchant_id=m.id, product_id=p_laptop.id, price=Decimal('1000.00'), mrp=Decimal('1200.00'))
    i_laptop = Inventory(offer_id=o_laptop.id, quantity=10)
    
    # 2. Mouse (High margin for upsell: mrp=100, price=50 -> 50% margin)
    p_mouse = Product(id=str(uuid.uuid4()), merchant_id=m.id, sku=f"SKU-MOU-{uuid.uuid4().hex[:6]}", name="Test Mouse", category="Electronics")
    o_mouse = Offer(id=str(uuid.uuid4()), merchant_id=m.id, product_id=p_mouse.id, price=Decimal('50.00'), mrp=Decimal('100.00'))
    i_mouse = Inventory(offer_id=o_mouse.id, quantity=10)
    
    # 3. Limited Item (Inventory = 1 for concurrency test)
    p_lim = Product(id=str(uuid.uuid4()), merchant_id=m.id, sku=f"SKU-LIM-{uuid.uuid4().hex[:6]}", name="Test Limited Art", category="Art")
    o_lim = Offer(id=str(uuid.uuid4()), merchant_id=m.id, product_id=p_lim.id, price=Decimal('500.00'), mrp=Decimal('500.00'))
    i_lim = Inventory(offer_id=o_lim.id, quantity=1)
    
    # 4. Expensive Item (For policy rejection)
    p_exp = Product(id=str(uuid.uuid4()), merchant_id=m.id, sku=f"SKU-EXP-{uuid.uuid4().hex[:6]}", name="Test Expensive TV", category="Electronics")
    o_exp = Offer(id=str(uuid.uuid4()), merchant_id=m.id, product_id=p_exp.id, price=Decimal('5000.00'), mrp=Decimal('5000.00'))
    i_exp = Inventory(offer_id=o_exp.id, quantity=10)

    db.add_all([m, c, u, api_key, p_laptop, o_laptop, i_laptop, p_mouse, o_mouse, i_mouse, p_lim, o_lim, i_lim, p_exp, o_exp, i_exp])
    
    # Agentic Authorization for the customer (Limit: 2000)
    auth = AgenticPaymentAuthorization(
        id=str(uuid.uuid4()),
        customer_id=c.id,
        merchant_id=m.id,
        status="ACTIVE",
        rail="WALLET",
        provider="internal",
        per_transaction_limit=Decimal('2000.00'),
        daily_limit=Decimal('5000.00'),
        spent_today=Decimal('0.00'),
        expires_at=None
    )
    db.add(auth)
    
    db.commit()
    
    return {
        "m_id": str(m.id),
        "c_id": str(c.id),
        "api_key": api_key_val,
        "cust_token": cust_token,
        "o_laptop": str(o_laptop.id),
        "o_mouse": str(o_mouse.id),
        "o_lim": str(o_lim.id),
        "o_exp": str(o_exp.id)
    }

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

async def run_scenario_1(data):
    print("\n--- SCENARIO 1: HAPPY PATH ---")
    async with httpx.AsyncClient(timeout=120) as client:
        # Chat 1: "I want to buy the Test Laptop"
        res = await client.post(f"{API_URL}/api/agent/chat", headers={"Authorization": f"Bearer {data['cust_token']}"}, json={
            "session_id": "sess_1",
            "merchant_id": data["m_id"],
            "customer_id": data["c_id"],
            "message": "I want to buy the Test Laptop"
        })
        print(f"Chat 1 Response: {res.status_code}")
        data_res = parse_stream(res)
        print(f"Agent Message: {data_res.get('message')}")
        
        # Check if agent called suggest_upsell
        suggestions = data_res.get('upsell_suggestions', [])
        print(f"Upsell Suggestions: {suggestions}")
        
        # Decline upsell
        if suggestions:
            # Accept upsell
            res = await client.post(f"{API_URL}/api/agent/upsell/response", headers={"Authorization": f"Bearer {data['cust_token']}"}, json={
                "session_id": "sess_1",
                "customer_id": data["c_id"],
                "accepted": False
            })
        
        # Chat 2: "Yes checkout"
        res2 = await client.post(f"{API_URL}/api/agent/chat", headers={"Authorization": f"Bearer {data['cust_token']}"}, json={
            "session_id": "sess_1",
            "merchant_id": data["m_id"],
            "customer_id": data["c_id"],
            "message": "I declined the upsell, please checkout now"
        })
        print(f"Chat 2 Response: {res2.status_code}")
        print(f"Agent Message: {parse_stream(res2).get('message')}")
        
        # DB Verification
        db = SessionLocal()
        decisions = db.query(AgentDecision).filter_by(customer_id=data["c_id"]).all()
        print(f"Agent Decisions for Customer: {[str(d.decision_type) + ' - ' + str(d.decision_status) for d in decisions]}")
        
        audit_logs = db.query(AuditLog).filter_by(merchant_id=data["m_id"]).all()
        print(f"Audit Logs for Merchant: {[l.action for l in audit_logs]}")
        db.close()

async def run_scenario_2(data):
    print("\n--- SCENARIO 2: POLICY REJECTION ---")
    async with httpx.AsyncClient(timeout=120) as client:
        # Chat 1: "I want to buy the Test Expensive TV" (costs 5000, limit is 2000)
        res = await client.post(f"{API_URL}/api/agent/chat", headers={"Authorization": f"Bearer {data['cust_token']}"}, json={
            "session_id": "sess_2",
            "merchant_id": data["m_id"],
            "customer_id": data["c_id"],
            "message": "I want to buy the Test Expensive TV and execute payment"
        })
        print(f"Chat 1 Response: {res.status_code}")
        data_res = parse_stream(res)
        print(f"Agent Message: {data_res.get('message')}")
        
        # DB Verification
        db = SessionLocal()
        decisions = db.query(AgentDecision).filter_by(customer_id=data["c_id"], decision_status="REJECTED").all()
        print(f"Rejected Decisions: {[d.reason for d in decisions]}")
        db.close()

async def run_scenario_3(data):
    print("\n--- SCENARIO 3: STOCK EXHAUSTION CONCURRENCY ---")
    # Need to simulate 2 users trying to buy the limited item
    db = SessionLocal()
    from app.models.user import User
    from app.core.security import create_access_token, get_password_hash
    c2 = Customer(id=str(uuid.uuid4()), merchant_id=data["m_id"], name="Cust 2", email=f"c2_{uuid.uuid4()}@cust.com")
    u2 = User(id=str(uuid.uuid4()), email=c2.email, hashed_password=get_password_hash("testpass"), role="CUSTOMER", full_name="Cust 2")
    db.add_all([c2, u2])
    db.commit()
    c2_id = str(c2.id)
    c2_token = create_access_token({"sub": c2.email})
    db.close()
    
    async with httpx.AsyncClient(timeout=120) as client:
        # Both ask to buy Test Limited Art
        async def try_buy(c_id, sess_id, token):
            return await client.post(f"{API_URL}/api/agent/chat", headers={"Authorization": f"Bearer {token}"}, json={
                "session_id": sess_id,
                "merchant_id": data["m_id"],
                "customer_id": c_id,
                "message": f"I want to buy the Test Limited Art {str(data['o_lim'])} and pay immediately"
            })
            
        r1, r2 = await asyncio.gather(
            try_buy(data["c_id"], "sess_3_1", data['cust_token']),
            try_buy(c2_id, "sess_3_2", c2_token)
        )
        print(f"Req 1: {r1.status_code}, Msg: {parse_stream(r1).get('message')}")
        print(f"Req 2: {r2.status_code}, Msg: {parse_stream(r2).get('message')}")

async def run_scenario_4(data):
    print("\n--- SCENARIO 4: EXTERNAL AGENT FLOW ---")
    async with httpx.AsyncClient(timeout=120) as client:
        headers = {"x-api-key": data["api_key"]}
        
        # 1. Catalog
        res_cat = await client.get(f"{API_URL}/api/agent-catalog.json", headers=headers)
        print(f"Catalog Response: {res_cat.status_code}")
        
        # 2. Checkout Intent
        res_intent = await client.post(f"{API_URL}/api/agent/checkout-intent", headers=headers, json={
            "items": [{"offer_id": data["o_laptop"], "quantity": 1}],
            "customer_email": "external@cust.com"
        })
        print(f"Intent Response: {res_intent.status_code}")
        
        if res_intent.status_code == 200:
            intent_data = res_intent.json()
            token = intent_data.get("token")
            print(f"Intent Token: {token}")
            
            # 3. Confirm
            res_conf = await client.post(f"{API_URL}/api/agent/checkout-intent/{token}/confirm")
            print(f"Confirm Response: {res_conf.status_code}")
            
async def main():
    print("Setting up data...")
    data = await setup_data()
    print(f"Data: {data}")
    
    print("\nNote: Adding 15-second delays between scenarios to stay within Gemini free-tier rate limits (15 RPM).")
    await run_scenario_1(data)
    await asyncio.sleep(15)
    await run_scenario_2(data)
    await asyncio.sleep(15)
    await run_scenario_3(data)
    await asyncio.sleep(15)
    await run_scenario_4(data)

if __name__ == "__main__":
    asyncio.run(main())

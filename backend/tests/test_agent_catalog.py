import pytest
from decimal import Decimal
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.product import Product, Inventory
from app.models.offer import Offer
from app.models.user import User
from app.models.order import Order, Payment
from app.core.security import get_password_hash, create_access_token
from app.payment.agentic_service import setup_agentic_authorization

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def setup_data():
    db = SessionLocal()
    
    # Create merchant
    m_id = str(uuid.uuid4())
    merchant = Merchant(id=m_id, name="Test Catalog Merchant", email="cat@merch.com", is_active=True)
    db.add(merchant)
    
    # Create user for merchant
    u_id = str(uuid.uuid4())
    user = User(
        id=u_id,
        email=f"admin_{u_id}@catmerch.com",
        hashed_password=get_password_hash("password"),
        role="MERCHANT_ADMIN",
        merchant_id=m_id,
        is_active=True
    )
    db.add(user)
    
    # Create customer
    c_id = str(uuid.uuid4())
    customer = Customer(id=c_id, merchant_id=m_id, name="Cat Cust", email="cat@c.com")
    db.add(customer)
    
    # Create product, offer, inventory
    p_id = str(uuid.uuid4())
    sku_val = f"SKU-{uuid.uuid4().hex[:6]}"
    prod = Product(id=p_id, merchant_id=m_id, sku=sku_val, name="Cat Product")
    db.add(prod)
    db.flush()
    
    o_id = str(uuid.uuid4())
    offer = Offer(id=o_id, merchant_id=m_id, product_id=p_id, price=Decimal('500.00'))
    db.add(offer)
    db.flush()
    
    inv_id = str(uuid.uuid4())
    inv = Inventory(id=inv_id, offer_id=o_id, quantity=10)
    db.add(inv)
    
    db.commit()
    
    token = create_access_token({"sub": user.email, "role": user.role})
    
    return {
        "db": db,
        "merchant_id": m_id,
        "customer_id": c_id,
        "offer_id": o_id,
        "product_id": p_id,
        "token": token
    }

def test_agent_catalog_returns_current_prices(client, setup_data):
    db = setup_data["db"]
    token = setup_data["token"]
    
    # 1. Fetch catalog
    res = client.get("/api/agent-catalog.json", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    catalog = res.json()
    assert len(catalog) >= 1
    
    item = next((x for x in catalog if x["offer_id"] == setup_data["offer_id"]), None)
    assert item is not None
    assert item["price"] == "500.00"
    assert item["inventory"] == 10
    
    # 2. Update price in DB
    offer = db.query(Offer).filter(Offer.id == setup_data["offer_id"]).first()
    offer.price = Decimal('450.00')
    db.commit()
    
    # 3. Fetch again and verify price updated
    res2 = client.get("/api/agent-catalog.json", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 200
    catalog2 = res2.json()
    item2 = next((x for x in catalog2 if x["offer_id"] == setup_data["offer_id"]), None)
    assert item2["price"] == "450.00"

def test_checkout_intent_respects_policy(client, setup_data):
    # Try to buy 100 qty, which exceeds inventory
    m_id = setup_data["merchant_id"]
    token = setup_data["token"]
    o_id = setup_data["offer_id"]
    c_id = setup_data["customer_id"]
    
    res = client.post("/api/agent/checkout-intent", headers={"Authorization": f"Bearer {token}"}, json={
        "merchant_id": m_id,
        "offer_id": o_id,
        "quantity": 100, # Exceeds 10
        "requesting_agent_id": "agent-123",
        "customer_id": c_id
    })
    
    assert res.status_code == 400
    assert "INSUFFICIENT_INVENTORY" in res.json()["detail"]

def test_checkout_intent_and_confirm_triggers_payment(client, setup_data):
    db = setup_data["db"]
    m_id = setup_data["merchant_id"]
    token = setup_data["token"]
    o_id = setup_data["offer_id"]
    c_id = setup_data["customer_id"]
    
    # 1. Setup agentic authorization for the customer so execute_agentic_payment succeeds
    setup_agentic_authorization(db, m_id, c_id, Decimal('5000'), Decimal('10000'))
    
    # 2. Create checkout intent
    res = client.post("/api/agent/checkout-intent", headers={"Authorization": f"Bearer {token}"}, json={
        "merchant_id": m_id,
        "offer_id": o_id,
        "quantity": 1,
        "requesting_agent_id": "agent-456",
        "customer_id": c_id
    })
    
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "pending_approval"
    cart_id = data["token"]
    assert data["confirm_url"] == f"/api/agent/checkout-intent/{cart_id}/confirm"
    
    # 3. Confirm checkout intent
    res2 = client.post(data["confirm_url"], headers={"Authorization": f"Bearer {token}"})
    
    assert res2.status_code == 200
    confirm_data = res2.json()
    assert confirm_data["status"] == "success"
    
    # 4. Verify order paid
    payment_id = confirm_data["payment_id"]
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    assert payment is not None
    assert payment.order.status == "PAID"

def test_external_agent_flow_with_api_key(client, setup_data):
    db = setup_data["db"]
    m_id = setup_data["merchant_id"]
    o_id = setup_data["offer_id"]
    c_id = setup_data["customer_id"]
    
    # 1. Setup MerchantAPIKey
    import hashlib
    raw_key = "sk_live_agent123"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    
    from app.models.merchant import MerchantAPIKey
    api_key = MerchantAPIKey(
        merchant_id=m_id,
        key_hash=key_hash,
        name="External AI Buyer"
    )
    db.add(api_key)
    db.commit()
    
    # Also ensure agentic auth is setup for the payment to succeed
    setup_agentic_authorization(db, m_id, c_id, Decimal('5000'), Decimal('10000'))
    
    headers = {"x-api-key": raw_key}
    
    # 2. Fetch catalog using ONLY API key
    res_catalog = client.get("/api/agent-catalog.json", headers=headers)
    assert res_catalog.status_code == 200, res_catalog.text
    catalog = res_catalog.json()
    assert len(catalog) >= 1
    
    # 3. Create checkout intent using ONLY API key
    res_intent = client.post("/api/agent/checkout-intent", headers=headers, json={
        "merchant_id": m_id,
        "offer_id": o_id,
        "quantity": 1,
        "requesting_agent_id": "google-agent-x",
        "customer_id": c_id
    })
    assert res_intent.status_code == 200, res_intent.text
    intent_data = res_intent.json()
    assert intent_data["status"] == "pending_approval"
    confirm_url = intent_data["confirm_url"]
    
    # 4. Confirm checkout intent using ONLY API key
    res_confirm = client.post(confirm_url, headers=headers)
    assert res_confirm.status_code == 200, res_confirm.text
    confirm_data = res_confirm.json()
    assert confirm_data["status"] == "success"
    
    # Verify payment success
    payment_id = confirm_data["payment_id"]
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    assert payment is not None
    assert payment.order.status == "PAID"


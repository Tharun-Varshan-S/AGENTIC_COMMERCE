import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.merchant import Merchant, MerchantRule
from app.models.customer import Customer
from app.models.product import Product, Inventory
from app.models.order import Cart, CartItem
from datetime import datetime, timezone
import uuid

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def setup_data():
    db = SessionLocal()
    merchant_id = str(uuid.uuid4())
    merchant = Merchant(id=merchant_id, name="Test Merchant", email="test@merch.com")
    db.add(merchant)
    
    rule = MerchantRule(
        merchant_id=merchant_id,
        max_transaction_amount=Decimal('5000'),
        max_discount_percent=Decimal('15'),
        min_margin_percent=Decimal('10'),
        auto_approval_limit=Decimal('3000'),
        require_consent=True
    )
    db.add(rule)
    
    customer_id = str(uuid.uuid4())
    customer = Customer(id=customer_id, merchant_id=merchant_id, name="Test Cust", email="c@c.com")
    db.add(customer)
    
    prod1_id = str(uuid.uuid4())
    sku_val = f"P1-{str(uuid.uuid4())[:8]}"
    prod1 = Product(id=prod1_id, merchant_id=merchant_id, sku=sku_val, name="P1", category="C", price=Decimal('1000'), cost_price=Decimal('500'))
    inv1 = Inventory(product_id=prod1_id, quantity=10, reserved_quantity=0)
    db.add(prod1)
    db.add(inv1)
    
    db.commit()
    yield {"db": db, "merchant_id": merchant_id, "customer_id": customer_id, "prod1_id": prod1_id}
    db.close()

def test_evaluate_policy_allowed(client, setup_data):
    db = setup_data["db"]
    m_id = setup_data["merchant_id"]
    c_id = setup_data["customer_id"]
    p_id = setup_data["prod1_id"]
    
    # Cart total = 2000 (under 3000 auto limit)
    cart_id = str(uuid.uuid4())
    cart = Cart(id=cart_id, merchant_id=m_id, customer_id=c_id)
    ci1 = CartItem(cart_id=cart_id, product_id=p_id, quantity=2, unit_price=Decimal('1000'))
    db.add(cart)
    db.add(ci1)
    db.commit()
    
    res = client.post("/api/policy/evaluate", json={"merchant_id": m_id, "customer_id": c_id, "cart_id": cart_id})
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "ALLOWED"

def test_evaluate_policy_requires_consent(client, setup_data):
    db = setup_data["db"]
    m_id = setup_data["merchant_id"]
    c_id = setup_data["customer_id"]
    p_id = setup_data["prod1_id"]
    
    # Cart total = 4000 (above 3000 auto limit, below 5000 max limit)
    cart_id = str(uuid.uuid4())
    cart = Cart(id=cart_id, merchant_id=m_id, customer_id=c_id)
    ci1 = CartItem(cart_id=cart_id, product_id=p_id, quantity=4, unit_price=Decimal('1000'))
    db.add(cart)
    db.add(ci1)
    db.commit()
    
    res = client.post("/api/policy/evaluate", json={"merchant_id": m_id, "customer_id": c_id, "cart_id": cart_id})
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "REQUIRES_CONSENT"
    assert any(r["code"] == "ABOVE_AUTO_APPROVAL_LIMIT" for r in data["reasons"])

def test_evaluate_policy_rejected(client, setup_data):
    db = setup_data["db"]
    m_id = setup_data["merchant_id"]
    c_id = setup_data["customer_id"]
    p_id = setup_data["prod1_id"]
    
    # Cart total = 6000 (above 5000 max limit)
    cart_id = str(uuid.uuid4())
    cart = Cart(id=cart_id, merchant_id=m_id, customer_id=c_id)
    ci1 = CartItem(cart_id=cart_id, product_id=p_id, quantity=6, unit_price=Decimal('1000'))
    db.add(cart)
    db.add(ci1)
    db.commit()
    
    res = client.post("/api/policy/evaluate", json={"merchant_id": m_id, "customer_id": c_id, "cart_id": cart_id})
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "REJECTED"
    assert any(r["code"] == "TRANSACTION_LIMIT_EXCEEDED" for r in data["reasons"])

def test_consent_flow(client, setup_data):
    db = setup_data["db"]
    m_id = setup_data["merchant_id"]
    c_id = setup_data["customer_id"]
    p_id = setup_data["prod1_id"]
    
    # Create cart requiring consent
    cart_id = str(uuid.uuid4())
    cart = Cart(id=cart_id, merchant_id=m_id, customer_id=c_id)
    ci1 = CartItem(cart_id=cart_id, product_id=p_id, quantity=4, unit_price=Decimal('1000'))
    db.add(cart)
    db.add(ci1)
    db.commit()
    
    # 1. Request consent
    res = client.post("/api/consent/request", json={"merchant_id": m_id, "customer_id": c_id, "cart_id": cart_id})
    if res.status_code != 200:
        print("ERROR:", res.json())
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "REQUIRES_CONSENT"
    consent_id = data["consent_id"]
    assert consent_id is not None
    
    # 2. Approve consent
    res = client.post(f"/api/consent/{consent_id}/approve")
    if res.status_code != 200:
        print("ERROR:", res.json())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "APPROVED"
    
    # 3. Policy evaluation should now be ALLOWED
    res = client.post("/api/policy/evaluate", json={"merchant_id": m_id, "customer_id": c_id, "cart_id": cart_id})
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] == "ALLOWED"

def test_consent_decline(client, setup_data):
    db = setup_data["db"]
    m_id = setup_data["merchant_id"]
    c_id = setup_data["customer_id"]
    p_id = setup_data["prod1_id"]
    
    # Create cart requiring consent
    cart_id = str(uuid.uuid4())
    cart = Cart(id=cart_id, merchant_id=m_id, customer_id=c_id)
    ci1 = CartItem(cart_id=cart_id, product_id=p_id, quantity=4, unit_price=Decimal('1000'))
    db.add(cart)
    db.add(ci1)
    db.commit()
    
    res = client.post("/api/consent/request", json={"merchant_id": m_id, "customer_id": c_id, "cart_id": cart_id})
    consent_id = res.json()["consent_id"]
    
    # Decline consent
    res = client.post(f"/api/consent/{consent_id}/decline")
    if res.status_code != 200:
        print("ERROR decline:", res.json())
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "DECLINED"


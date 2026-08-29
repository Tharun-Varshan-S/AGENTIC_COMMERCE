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
from app.models.order import Cart, CartItem
from app.models.agent import AgentDecision

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def setup_data():
    db = SessionLocal()
    
    # Create two merchants
    merchant_A_id = str(uuid.uuid4())
    merchant_A = Merchant(id=merchant_A_id, name="Merchant A", email="a@merch.com")
    db.add(merchant_A)
    
    merchant_B_id = str(uuid.uuid4())
    merchant_B = Merchant(id=merchant_B_id, name="Merchant B", email="b@merch.com")
    db.add(merchant_B)

    # Create a customer associated with Merchant A
    customer_id = str(uuid.uuid4())
    customer = Customer(id=customer_id, merchant_id=merchant_A_id, name="Test Cust", email="c@c.com")
    db.add(customer)
    
    # Create product and offer for Merchant B
    prod_id = str(uuid.uuid4())
    sku_val = f"P1-{str(uuid.uuid4())[:8]}"
    prod = Product(id=prod_id, merchant_id=merchant_B_id, sku=sku_val, name="P1", category="C")
    db.add(prod)
    db.flush()
    
    offer_id = str(uuid.uuid4())
    offer = Offer(id=offer_id, merchant_id=merchant_B_id, product_id=prod_id, price=Decimal('100.00'))
    db.add(offer)
    db.flush()
    
    db.commit()

    return {
        "db": db,
        "merchant_A_id": merchant_A_id,
        "merchant_B_id": merchant_B_id,
        "customer_id": customer_id,
        "product_id": prod_id,
        "offer_id": offer_id,
    }

def test_agentic_payment_merchant_mismatch(client, setup_data):
    db = setup_data["db"]
    m_A_id = setup_data["merchant_A_id"]
    m_B_id = setup_data["merchant_B_id"]
    c_id = setup_data["customer_id"]
    o_id = setup_data["offer_id"]

    # 1. Setup agentic authorization for Merchant A
    res = client.post("/api/payments/authorization/setup", json={
        "merchant_id": m_A_id,
        "customer_id": c_id,
        "per_transaction_limit": 5000,
        "daily_limit": 10000
    })
    assert res.status_code == 200

    # 2. Create a cart for Merchant B
    cart_id = str(uuid.uuid4())
    cart = Cart(id=cart_id, merchant_id=m_B_id, customer_id=c_id)
    ci = CartItem(cart_id=cart_id, offer_id=o_id, quantity=1, unit_price=Decimal('100.00'))
    db.add(cart)
    db.add(ci)
    db.commit()

    # 3. Execute agentic payment against cart from Merchant B
    res = client.post("/api/payments/execute-agentic", json={
        "merchant_id": m_B_id,
        "customer_id": c_id,
        "cart_id": cart_id
    })
    
    # 4. Assert rejection
    assert res.status_code == 400
    assert "authorization_merchant_mismatch" in res.json()["detail"]

    # 5. Assert AgentDecision is logged with REJECTED and correct rule name
    decision = db.query(AgentDecision).filter(
        AgentDecision.customer_id == c_id,
        AgentDecision.merchant_id == m_B_id,
        AgentDecision.action == "AGENTIC_PAYMENT_EXECUTION"
    ).first()
    
    assert decision is not None
    assert decision.decision_status == "REJECTED"
    assert "authorization_merchant_mismatch" in decision.policy_rules

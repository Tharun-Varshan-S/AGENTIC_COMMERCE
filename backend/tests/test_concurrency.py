import pytest
import uuid
import concurrent.futures
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.product import Product, Inventory
from app.models.offer import Offer
from app.models.order import Cart, CartItem
from app.models.agent import AgentDecision
from app.payment.agentic_service import setup_agentic_authorization

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def setup_data():
    db = SessionLocal()
    
    # Create merchant
    merchant_id = str(uuid.uuid4())
    merchant = Merchant(id=merchant_id, name="Merchant C", email="c@merch.com")
    db.add(merchant)
    
    # Create customer
    customer_id = str(uuid.uuid4())
    customer = Customer(id=customer_id, merchant_id=merchant_id, name="Cust C", email="c2@c.com")
    db.add(customer)
    
    # Create product
    prod_id = str(uuid.uuid4())
    sku_val = f"P2-{str(uuid.uuid4())[:8]}"
    prod = Product(id=prod_id, merchant_id=merchant_id, sku=sku_val, name="P2", category="C")
    db.add(prod)
    db.flush()
    
    # Create offer
    offer_id = str(uuid.uuid4())
    offer = Offer(id=offer_id, merchant_id=merchant_id, product_id=prod_id, price=Decimal('100.00'))
    db.add(offer)
    db.flush()
    
    # Setup Inventory with quantity=1
    inventory = Inventory(offer_id=offer_id, quantity=1)
    db.add(inventory)
    
    db.commit()

    return {
        "db": db,
        "merchant_id": merchant_id,
        "customer_id": customer_id,
        "product_id": prod_id,
        "offer_id": offer_id,
    }

def test_concurrent_agentic_payment(client, setup_data):
    db = setup_data["db"]
    m_id = setup_data["merchant_id"]
    c_id = setup_data["customer_id"]
    o_id = setup_data["offer_id"]

    # 1. Setup agentic authorization
    setup_agentic_authorization(db, m_id, c_id, Decimal('5000'), Decimal('10000'))

    # 2. Create two identical carts for the same offer
    cart1_id = str(uuid.uuid4())
    cart1 = Cart(id=cart1_id, merchant_id=m_id, customer_id=c_id)
    ci1 = CartItem(cart_id=cart1_id, offer_id=o_id, quantity=1, unit_price=Decimal('100.00'))
    
    cart2_id = str(uuid.uuid4())
    cart2 = Cart(id=cart2_id, merchant_id=m_id, customer_id=c_id)
    ci2 = CartItem(cart_id=cart2_id, offer_id=o_id, quantity=1, unit_price=Decimal('100.00'))
    
    db.add(cart1)
    db.add(ci1)
    db.add(cart2)
    db.add(ci2)
    db.commit()

    # 3. Fire concurrent requests
    def execute_payment(cart_id_val):
        # We need a new session in the thread if we do db operations, but the client does it via endpoints which manage their own sessions!
        # The endpoints use a dependency `get_db` that yields a new session.
        return client.post("/api/payments/execute-agentic", json={
            "merchant_id": m_id,
            "customer_id": c_id,
            "cart_id": cart_id_val
        })

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(execute_payment, cart1_id)
        future2 = executor.submit(execute_payment, cart2_id)
        
        res1 = future1.result()
        res2 = future2.result()

        # 4. Assert exactly one success and one failure
        statuses = [res1.status_code, res2.status_code]
        assert statuses.count(200) == 1, f"Expected exactly one success, got statuses: {statuses}, res1={res1.text}, res2={res2.text}"
    assert statuses.count(400) == 1, f"Expected exactly one failure, got statuses: {statuses}"
    
    # 5. Assert the failure is due to insufficient_stock
    failed_res = res1 if res1.status_code == 400 else res2
    assert "Insufficient inventory" in failed_res.json()["detail"]

    # 6. Assert exactly one AgentDecision logged with insufficient_stock
    db.expire_all() # ensure we fetch fresh from DB
    decisions = db.query(AgentDecision).filter(
        AgentDecision.customer_id == c_id,
        AgentDecision.merchant_id == m_id,
        AgentDecision.action == "AGENTIC_PAYMENT_EXECUTION",
        AgentDecision.decision_status == "REJECTED"
    ).all()
    
    insufficient_stock_decisions = [d for d in decisions if "insufficient_stock" in d.policy_rules]
    assert len(insufficient_stock_decisions) == 1

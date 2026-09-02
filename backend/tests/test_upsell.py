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

@pytest.fixture
def setup_upsell_data():
    db = SessionLocal()
    
    # Merchant & Customer
    m_id = str(uuid.uuid4())
    c_id = str(uuid.uuid4())
    merchant = Merchant(id=m_id, name="Upsell Merchant", email="upsell@merch.com", is_active=True)
    customer = Customer(id=c_id, merchant_id=m_id, name="Upsell Cust", email="upsell@c.com")
    db.add_all([merchant, customer])
    
    # Primary Product (in cart)
    p_id1 = str(uuid.uuid4())
    prod1 = Product(id=p_id1, merchant_id=m_id, sku=f"SKU-{uuid.uuid4().hex[:6]}", name="Primary Prod", category="Electronics")
    o_id1 = str(uuid.uuid4())
    offer1 = Offer(id=o_id1, merchant_id=m_id, product_id=p_id1, price=Decimal('100.00'), mrp=Decimal('100.00'))
    
    # Upsell Candidate Product (high margin, not in cart)
    p_id2 = str(uuid.uuid4())
    prod2 = Product(id=p_id2, merchant_id=m_id, sku=f"SKU-{uuid.uuid4().hex[:6]}", name="Upsell Prod", category="Electronics")
    o_id2 = str(uuid.uuid4())
    # 50% discount margin proxy -> (200-100)/200 = 0.5 > 0.2
    offer2 = Offer(id=o_id2, merchant_id=m_id, product_id=p_id2, price=Decimal('100.00'), mrp=Decimal('200.00'))
    
    db.add_all([prod1, offer1, prod2, offer2])
    
    # Cart
    cart_id = str(uuid.uuid4())
    cart = Cart(id=cart_id, customer_id=c_id, merchant_id=m_id)
    cart_item = CartItem(cart_id=cart_id, offer_id=o_id1, quantity=1, unit_price=Decimal('100.00'))
    db.add_all([cart, cart_item])
    
    db.commit()
    
    return {
        "db": db,
        "merchant_id": m_id,
        "customer_id": c_id,
        "cart_id": cart_id,
        "primary_offer": o_id1,
        "upsell_offer": o_id2
    }

def test_suggest_upsell_tool(setup_upsell_data):
    from app.tools.revenue_tools import SuggestUpsellTool
    db = setup_upsell_data["db"]
    tool = SuggestUpsellTool()
    
    res = tool.execute(
        db_session=db,
        merchant_id=setup_upsell_data["merchant_id"],
        customer_id=setup_upsell_data["customer_id"],
        cart_id=setup_upsell_data["cart_id"]
    )
    
    # Should suggest the upsell product
    assert len(res["suggestions"]) == 1
    assert res["suggestions"][0]["id"] == setup_upsell_data["upsell_offer"]
    
    # Check decision logged
    decision = db.query(AgentDecision).filter(
        AgentDecision.decision_type == "upsell_suggestion",
        AgentDecision.merchant_id == setup_upsell_data["merchant_id"]
    ).first()
    assert decision is not None
    assert str(decision.recommended_product_id) == str(db.query(Offer).filter_by(id=setup_upsell_data["upsell_offer"]).first().product_id)

def test_upsell_decline(client, setup_upsell_data):
    db = setup_upsell_data["db"]
    
    # Initial cart items count
    cart_items_count = db.query(CartItem).filter(CartItem.cart_id == setup_upsell_data["cart_id"]).count()
    
    res = client.post("/api/upsell/response", json={
        "merchant_id": setup_upsell_data["merchant_id"],
        "customer_id": setup_upsell_data["customer_id"],
        "cart_id": setup_upsell_data["cart_id"],
        "offer_id": setup_upsell_data["upsell_offer"],
        "action": "decline"
    })
    
    assert res.status_code == 200
    
    # Assert cart has not changed
    new_cart_items_count = db.query(CartItem).filter(CartItem.cart_id == setup_upsell_data["cart_id"]).count()
    assert new_cart_items_count == cart_items_count
    
    # Assert decision logged
    decision = db.query(AgentDecision).filter(AgentDecision.decision_status == "DECLINED").first()
    assert decision is not None

def test_upsell_accept(client, setup_upsell_data):
    db = setup_upsell_data["db"]
    
    # Initial cart items count
    cart_items_count = db.query(CartItem).filter(CartItem.cart_id == setup_upsell_data["cart_id"]).count()
    
    res = client.post("/api/upsell/response", json={
        "merchant_id": setup_upsell_data["merchant_id"],
        "customer_id": setup_upsell_data["customer_id"],
        "cart_id": setup_upsell_data["cart_id"],
        "offer_id": setup_upsell_data["upsell_offer"],
        "action": "accept"
    })
    
    assert res.status_code == 200
    
    # Assert cart has changed
    new_cart_items_count = db.query(CartItem).filter(CartItem.cart_id == setup_upsell_data["cart_id"]).count()
    assert new_cart_items_count == cart_items_count + 1
    
    # Assert decision logged
    decision = db.query(AgentDecision).filter(AgentDecision.decision_status == "ACCEPTED").first()
    assert decision is not None

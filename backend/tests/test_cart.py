import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.customer import Customer
from app.models.merchant import Merchant
from app.models.product import Product, Inventory
from app.models.offer import Offer
from decimal import Decimal
import uuid

client = TestClient(app)

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_product_max_price_filtering():
    response = client.get("/api/products?max_price=2000")
    assert response.status_code == 200
    data = response.json()
    for product in data:
        assert float(product["price"]) <= 2000

def test_cart_creation(db):
    merchant = db.query(Merchant).first()
    customer = Customer(merchant_id=merchant.id, name="Test Cust", email=f"test{uuid.uuid4().hex}@test.com")
    db.add(customer)
    db.commit()
    
    response = client.post(
        "/api/carts",
        json={"customer_id": str(customer.id), "merchant_id": str(merchant.id)}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == str(customer.id)
    assert data["merchant_id"] == str(merchant.id)
    assert data["status"] == "ACTIVE"
    assert data["items"] == []
    assert float(data["subtotal"]) == 0.0

def test_cart_add_item_and_subtotal(db):
    merchant = db.query(Merchant).first()
    customer = Customer(merchant_id=merchant.id, name="Test Cust", email=f"test{uuid.uuid4().hex}@test.com")
    db.add(customer)
    db.commit()
    
    # Create product with offer and inventory
    product = Product(merchant_id=merchant.id, sku=f"TEST-{uuid.uuid4().hex[:8]}", name="Test Item", category="Test")
    db.add(product)
    db.flush()
    offer = Offer(product_id=product.id, merchant_id=merchant.id, price=Decimal("150.00"))
    db.add(offer)
    db.flush()
    db.add(Inventory(offer_id=offer.id, quantity=100))
    db.commit()
    
    # Get active cart
    response = client.get(f"/api/carts/active?customer_id={str(customer.id)}")
    if response.status_code == 404:
        merchant = db.query(Merchant).first()
        response = client.post(
            "/api/carts",
            json={"customer_id": str(customer.id), "merchant_id": str(merchant.id)}
        )
    
    cart = response.json()
    cart_id = cart["id"]
    
    # Add item
    response = client.post(
        f"/api/carts/{cart_id}/items",
        json={"product_id": str(product.id), "quantity": 1}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    
    # verify subtotal calculation
    expected_subtotal = sum(item["quantity"] * float(item["unit_price"]) for item in data["items"])
    assert float(data["subtotal"]) == expected_subtotal
    
def test_cart_exceed_inventory(db):
    merchant = db.query(Merchant).first()
    customer = Customer(merchant_id=merchant.id, name="Test Cust", email=f"test{uuid.uuid4().hex}@test.com")
    db.add(customer)
    db.commit()
    
    product = Product(merchant_id=merchant.id, sku=f"TEST-{uuid.uuid4().hex[:8]}", name="Test Item", category="Test")
    db.add(product)
    db.flush()
    offer = Offer(product_id=product.id, merchant_id=merchant.id, price=Decimal("150.00"))
    db.add(offer)
    db.flush()
    db.add(Inventory(offer_id=offer.id, quantity=5))
    db.commit()
    
    response = client.get(f"/api/carts/active?customer_id={str(customer.id)}")
    if response.status_code == 404:
        response = client.post(
            "/api/carts",
            json={"customer_id": str(customer.id), "merchant_id": str(merchant.id)}
        )
    cart_id = response.json()["id"]
    
    # Try adding a huge quantity
    response = client.post(
        f"/api/carts/{cart_id}/items",
        json={"product_id": str(product.id), "quantity": 9999}
    )
    assert response.status_code == 400
    assert "units are currently available" in response.json()["detail"]

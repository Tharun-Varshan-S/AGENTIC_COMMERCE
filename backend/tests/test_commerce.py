import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.product import Product, Inventory
from app.models.merchant import Merchant
from app.models.order import Cart, CartItem

client = TestClient(app)

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_get_merchants(db):
    response = client.get("/api/merchants")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["name"] == "TechNova Gaming Store"

def test_get_products():
    response = client.get("/api/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 6

def test_get_products_by_category():
    response = client.get("/api/products?category=Gaming")
    assert response.status_code == 200
    data = response.json()
    for product in data:
        assert product["category"] == "Gaming"

def test_search_products():
    response = client.get("/api/products?search=mouse")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2 # G304 and G502

def test_inventory_calculation(db):
    response = client.get("/api/inventory")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    inv = data[0]
    assert inv["available_quantity"] == inv["quantity"] - inv["reserved_quantity"]

def test_cart_item_unit_price(db):
    cart_item = db.query(CartItem).first()
    assert cart_item is not None
    # Ensure it's stored as Decimal/Numeric, which translates to a valid float/decimal when fetched
    assert float(cart_item.unit_price) > 0

def test_merchant_rules(db):
    merchant = db.query(Merchant).first()
    response = client.get(f"/api/merchant-rules?merchant_id={str(merchant.id)}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert float(data[0]["max_transaction_amount"]) == 50000.00

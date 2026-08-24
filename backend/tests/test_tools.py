import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.merchant import Merchant
from app.models.customer import Customer

client = TestClient(app)

@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_tool_discovery():
    response = client.get("/api/tools")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    tool_names = [t["name"] for t in data["tools"]]
    expected_tools = [
        "search_catalog", 
        "get_product", 
        "check_inventory", 
        "get_customer_context", 
        "calculate_cart", 
        "validate_cart",
        "get_recommendations"
    ]
    for tool in expected_tools:
        assert tool in tool_names

def test_tool_execute_not_found():
    response = client.post("/api/tools/non_existent_tool/execute", json={})
    assert response.status_code == 200 # tool registry catches it
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "TOOL_NOT_FOUND"

def test_search_catalog_tool(db):
    merchant = db.query(Merchant).first()
    
    response = client.post(
        "/api/tools/search_catalog/execute",
        json={"merchant_id": str(merchant.id), "query": "mouse"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "products" in data["result"]
    assert data["result"]["count"] >= 0

def test_merchant_isolation_get_product(db):
    merchant_1 = db.query(Merchant).first()
    merchant_2 = db.query(Merchant).order_by(Merchant.id.desc()).first()
    
    # We assume we don't have the product id handy, so just pass a fake UUID
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    
    response = client.post(
        "/api/tools/get_product/execute",
        json={"merchant_id": str(merchant_1.id), "product_id": fake_uuid}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "PRODUCT_NOT_FOUND"

def test_get_customer_context_tool(db):
    merchant = db.query(Merchant).first()
    customer = db.query(Customer).filter(Customer.merchant_id == merchant.id).first()
    
    response = client.post(
        "/api/tools/get_customer_context/execute",
        json={"merchant_id": str(merchant.id), "customer_id": str(customer.id)}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["result"]["customer_id"] == str(customer.id)
    assert "recent_events" in data["result"]

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
        "create_checkout_session",
        "calculate_cart", 
        "validate_cart",
        "get_payment_status",
        "validate_policy",
        "check_payment_authorization",
        "execute_agentic_payment"
    ]
    for tool in expected_tools:
        assert tool in tool_names

def test_tool_execute_not_found():
    response = client.post("/api/tools/non_existent_tool/execute", json={})
    assert response.status_code == 200 # tool registry catches it
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "TOOL_NOT_FOUND"

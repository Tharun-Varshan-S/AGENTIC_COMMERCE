import pytest
import uuid
from decimal import Decimal
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.user import User
from app.core.security import create_access_token
from datetime import timedelta

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

@pytest.fixture(scope="module")
def setup_data():
    db = SessionLocal()
    
    # Create merchant user
    merchant_id = str(uuid.uuid4())
    merch_email = f"merch_{uuid.uuid4().hex[:8]}@test.com"
    merchant = Merchant(id=merchant_id, name="Test Merch", email=merch_email, is_active=True)
    db.add(merchant)
    
    user_m = User(
        email=merch_email,
        hashed_password="pw",
        role="MERCHANT_OWNER",
        merchant_id=merchant_id
    )
    db.add(user_m)
    
    # Create Customer A
    email_a = f"custA_{uuid.uuid4().hex[:8]}@test.com"
    user_a = User(email=email_a, hashed_password="pw", role="CUSTOMER")
    db.add(user_a)
    
    customer_a_id = str(uuid.uuid4())
    customer_a = Customer(id=customer_a_id, merchant_id=merchant_id, name="A", email=email_a)
    db.add(customer_a)
    
    # Create Customer B
    email_b = f"custB_{uuid.uuid4().hex[:8]}@test.com"
    user_b = User(email=email_b, hashed_password="pw", role="CUSTOMER")
    db.add(user_b)
    
    customer_b_id = str(uuid.uuid4())
    customer_b = Customer(id=customer_b_id, merchant_id=merchant_id, name="B", email=email_b)
    db.add(customer_b)
    
    db.commit()

    token_m = create_access_token(data={"sub": merch_email}, expires_delta=timedelta(minutes=60))
    token_a = create_access_token(data={"sub": email_a}, expires_delta=timedelta(minutes=60))
    token_b = create_access_token(data={"sub": email_b}, expires_delta=timedelta(minutes=60))

    return {
        "db": db,
        "merchant_id": merchant_id,
        "token_m": token_m,
        "token_a": token_a,
        "token_b": token_b,
        "customer_a_id": customer_a_id,
        "customer_b_id": customer_b_id,
    }

def test_auth_enforcement_401(client, setup_data):
    # No auth token provided
    res = client.get(f"/api/payments/authorization/status?customer_id={setup_data['customer_a_id']}")
    assert res.status_code == 401

def test_auth_enforcement_403(client, setup_data):
    # Customer B trying to access Customer A's resource
    res = client.get(
        f"/api/payments/authorization/status?customer_id={setup_data['customer_a_id']}",
        headers={"Authorization": f"Bearer {setup_data['token_b']}"}
    )
    assert res.status_code == 403

def test_auth_enforcement_200(client, setup_data):
    # Customer A accessing their own resource
    res = client.get(
        f"/api/payments/authorization/status?customer_id={setup_data['customer_a_id']}",
        headers={"Authorization": f"Bearer {setup_data['token_a']}"}
    )
    assert res.status_code == 200
    assert "status" in res.json()

def test_merchant_auth_enforcement(client, setup_data):
    # Public shouldn't access customers list
    res = client.get("/api/customers")
    assert res.status_code == 401
    
    # Customer shouldn't access customers list
    res = client.get(
        "/api/customers",
        headers={"Authorization": f"Bearer {setup_data['token_a']}"}
    )
    assert res.status_code == 403
    
    # Merchant can access
    res = client.get(
        "/api/customers",
        headers={"Authorization": f"Bearer {setup_data['token_m']}"}
    )
    assert res.status_code == 200
    # Should only return customers for this merchant (both A and B are under this merchant)
    data = res.json()
    assert isinstance(data, list)

def test_revoke_auth_enforcement_403(client, setup_data):
    # Customer B trying to revoke Customer A's resource
    res = client.post(
        f"/api/payments/authorization/revoke?customer_id={setup_data['customer_a_id']}",
        headers={"Authorization": f"Bearer {setup_data['token_b']}"}
    )
    assert res.status_code == 403

def test_get_active_authorization_filters_expired(setup_data):
    from app.payment.agentic_service import get_active_authorization
    from app.models.payment_authorization import AgenticPaymentAuthorization
    from datetime import datetime, timedelta
    
    db = setup_data["db"]
    
    # Clean up any existing active auths
    db.query(AgenticPaymentAuthorization).filter(
        AgenticPaymentAuthorization.customer_id == setup_data["customer_a_id"]
    ).delete()
    db.commit()

    # Create an expired authorization
    auth = AgenticPaymentAuthorization(
        customer_id=setup_data["customer_a_id"],
        merchant_id=setup_data["merchant_id"],
        provider="razorpay",
        rail="upi_reserve_pay",
        authorization_reference="auth_exp_123",
        status="ACTIVE",
        per_transaction_limit=100,
        daily_limit=500,
        spent_today=0,
        expires_at=datetime.utcnow() - timedelta(days=1)
    )
    db.add(auth)
    db.commit()
    
    active_auth = get_active_authorization(db, setup_data["customer_a_id"])
    assert active_auth is None
    
    # Cleanup
    db.delete(auth)
    db.commit()

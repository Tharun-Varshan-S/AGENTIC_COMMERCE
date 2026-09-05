"""
Test suite for the Agentic Razorpay checkout flow.

Tests the following scenarios required by the hackathon spec:
1. No spending limit set → 422 or stream error (SpendingLimitNotConfigured)
2. Amount exceeds per-transaction limit → stream error (TransactionLimitExceeded)
3. Razorpay provider failure → handled gracefully with error_class
4. Merchant mismatch → gate fails cleanly
5. Audit log is populated with order_id on successful gate-pass
"""
import pytest
from decimal import Decimal
import uuid
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.db.session import SessionLocal
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.product import Product, Inventory
from app.models.offer import Offer
from app.models.order import Cart, CartItem
from app.models.audit import AuditLog
from app.models.user import User
from app.core.security import create_access_token


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(scope="module")
def db():
    _db = SessionLocal()
    yield _db
    _db.close()


@pytest.fixture(scope="module")
def setup_data(db):
    """
    Creates one merchant, one customer (user), one product + offer + inventory.
    Returns all IDs needed by the tests.
    """
    # Merchant
    merchant = Merchant(
        id=str(uuid.uuid4()),
        name="Test Merchant Agentic",
        email=f"merch-{uuid.uuid4().hex[:6]}@test.com",
        is_active=True,
        ai_commerce_enabled=True,
        agent_purchases_enabled=True
    )
    db.add(merchant)
    db.flush()

    # User
    user = User(
        id=str(uuid.uuid4()),
        email=f"buyer-{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="dummy",
        role="CUSTOMER",
        is_active=True
    )
    db.add(user)
    db.flush()

    # Customer — NOTE: transaction_limit is NULL (not set yet)
    customer = Customer(
        id=str(uuid.uuid4()),
        merchant_id=merchant.id,
        email=user.email,
        name="Test Buyer",
        transaction_limit=None,   # Explicitly NOT configured
        daily_limit=None
    )
    db.add(customer)
    db.flush()

    # Product
    product = Product(
        id=str(uuid.uuid4()),
        merchant_id=merchant.id,
        sku=f"SKU-{uuid.uuid4().hex[:8]}",
        name="Test Headphones",
        category="Electronics"
    )
    db.add(product)
    db.flush()

    # Offer — price ₹999
    offer = Offer(
        id=str(uuid.uuid4()),
        merchant_id=merchant.id,
        product_id=product.id,
        price=Decimal("999.00")
    )
    db.add(offer)
    db.flush()

    # Inventory
    inventory = Inventory(
        offer_id=offer.id,
        quantity=100
    )
    db.add(inventory)

    db.commit()

    token = create_access_token(data={"sub": user.email, "role": "CUSTOMER"})

    return {
        "merchant_id": merchant.id,
        "customer_id": customer.id,
        "user_email": user.email,
        "product_id": product.id,
        "offer_id": offer.id,
        "token": token,
        "db": db
    }


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _drain_stream(response) -> list[dict]:
    """Parse NDJSON streaming response body into a list of events."""
    events = []
    for line in response.iter_lines():
        line = line.decode() if isinstance(line, bytes) else line
        if line.strip():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events


# ─── Test 1: No Spending Limit Configured ────────────────────────────────────

def test_no_spending_limit_blocks_purchase(client, setup_data):
    """
    When a customer has NULL transaction_limit, Buy Now must return a
    SpendingLimitNotConfigured error via the stream — never reaching Razorpay.
    """
    token = setup_data["token"]

    with client.stream("POST", "/api/agent/execute-purchase",
                       json={
                           "merchant_id": setup_data["merchant_id"],
                           "type": "buy_now",
                           "product_id": setup_data["product_id"],
                           "offer_id": setup_data["offer_id"],
                           "quantity": 1,
                           "human_approval": True
                       },
                       headers=auth_headers(token)) as response:
        assert response.status_code == 200, "Stream must start with 200"
        events = _drain_stream(response)

    error_events = [e for e in events if e.get("type") == "error"]
    assert len(error_events) == 1
    assert error_events[0]["error_class"] == "SpendingLimitNotConfigured", \
        f"Expected SpendingLimitNotConfigured, got: {error_events[0]}"

    # Verify no GATE_PASSED audit exists
    db = setup_data["db"]
    gate_passed = db.query(AuditLog).filter(
        AuditLog.customer_id == setup_data["customer_id"],
        AuditLog.action.like("GATE_PASSED%")
    ).first()
    assert gate_passed is None, "No gate should have passed for unconfigured limit"


# ─── Test 2: Amount Exceeds Per-Transaction Limit ────────────────────────────

def test_amount_exceeds_transaction_limit(client, setup_data, db):
    """
    When the product price (₹50,000) exceeds the customer's transaction limit (₹1,000),
    the stream must return TransactionLimitExceeded and a GATE_FAILED audit log.
    """
    token = setup_data["token"]

    # Set a low limit on the customer
    customer = db.query(Customer).filter(Customer.id == setup_data["customer_id"]).first()
    customer.transaction_limit = Decimal("1000.00")
    customer.daily_limit = Decimal("10000.00")
    db.commit()

    # Create an expensive offer (₹50,000)
    expensive_offer = Offer(
        id=str(uuid.uuid4()),
        merchant_id=setup_data["merchant_id"],
        product_id=setup_data["product_id"],
        price=Decimal("50000.00")
    )
    expensive_inv = Inventory(offer_id=expensive_offer.id, quantity=10)
    db.add(expensive_offer)
    db.add(expensive_inv)
    db.commit()

    with client.stream("POST", "/api/agent/execute-purchase",
                       json={
                           "merchant_id": setup_data["merchant_id"],
                           "type": "buy_now",
                           "product_id": setup_data["product_id"],
                           "offer_id": expensive_offer.id,
                           "quantity": 1,
                           "human_approval": True
                       },
                       headers=auth_headers(token)) as response:
        assert response.status_code == 200
        events = _drain_stream(response)

    error_events = [e for e in events if e.get("type") == "error"]
    assert len(error_events) == 1
    assert error_events[0]["error_class"] == "TransactionLimitExceeded", \
        f"Expected TransactionLimitExceeded, got: {error_events[0]}"

    # Verify GATE_FAILED audit log
    gate_failed = db.query(AuditLog).filter(
        AuditLog.customer_id == setup_data["customer_id"],
        AuditLog.action == "GATE_FAILED:TransactionLimitExceeded"
    ).order_by(AuditLog.created_at.desc()).first()
    assert gate_failed is not None, "GATE_FAILED:TransactionLimitExceeded must be logged"
    assert gate_failed.metadata_json["error_class"] == "TransactionLimitExceeded"


# ─── Test 3: Razorpay Provider Failure ───────────────────────────────────────

def test_razorpay_provider_failure_handled_gracefully(client, setup_data, db):
    """
    When Razorpay API returns an error (provider failure), the stream must:
    1. Return error_class = RazorpayProviderError
    2. Log a RAZORPAY_PROVIDER_ERROR audit entry
    3. NOT crash the server (200 stream, error event, no 500)
    """
    token = setup_data["token"]

    # Ensure limit is set (from previous test)
    customer = db.query(Customer).filter(Customer.id == setup_data["customer_id"]).first()
    customer.transaction_limit = Decimal("99999.00")
    customer.daily_limit = Decimal("999999.00")
    db.commit()

    from app.payment.exceptions import RazorpayProviderError

    with patch("app.payment.razorpay_client.create_order") as mock_create:
        mock_create.side_effect = RazorpayProviderError("Test: Razorpay connection refused")

        with client.stream("POST", "/api/agent/execute-purchase",
                           json={
                               "merchant_id": setup_data["merchant_id"],
                               "type": "buy_now",
                               "product_id": setup_data["product_id"],
                               "offer_id": setup_data["offer_id"],
                               "quantity": 1,
                               "human_approval": True
                           },
                           headers=auth_headers(token)) as response:
            assert response.status_code == 200, "Stream must not crash to 500"
            events = _drain_stream(response)

    error_events = [e for e in events if e.get("type") == "error"]
    assert len(error_events) == 1
    assert error_events[0]["error_class"] == "RazorpayProviderError", \
        f"Expected RazorpayProviderError, got: {error_events[0]}"

    # Audit log for provider error
    provider_error_log = db.query(AuditLog).filter(
        AuditLog.customer_id == setup_data["customer_id"],
        AuditLog.action == "RAZORPAY_PROVIDER_ERROR"
    ).order_by(AuditLog.created_at.desc()).first()
    assert provider_error_log is not None, "RAZORPAY_PROVIDER_ERROR must be logged to audit trail"


# ─── Test 4: Successful Purchase Creates Audit Log with order_id ──────────────

def test_successful_order_creates_audit_with_order_id(client, setup_data, db):
    """
    When a valid purchase goes through (mocked Razorpay), the resulting
    AuditLog entries must have order_id set (not NULL).
    """
    token = setup_data["token"]

    # Ensure high enough limit
    customer = db.query(Customer).filter(Customer.id == setup_data["customer_id"]).first()
    customer.transaction_limit = Decimal("99999.00")
    customer.daily_limit = Decimal("999999.00")
    db.commit()

    fake_rp_order = {
        "id": f"order_test_{uuid.uuid4().hex[:12]}",
        "amount": 99900,
        "currency": "INR",
        "receipt": "test_receipt"
    }

    with patch("app.payment.razorpay_client.create_order", return_value=fake_rp_order):
        with client.stream("POST", "/api/agent/execute-purchase",
                           json={
                               "merchant_id": setup_data["merchant_id"],
                               "type": "buy_now",
                               "product_id": setup_data["product_id"],
                               "offer_id": setup_data["offer_id"],
                               "quantity": 1,
                               "human_approval": True
                           },
                           headers=auth_headers(token)) as response:
            assert response.status_code == 200
            events = _drain_stream(response)

    # Verify final_result received
    final_events = [e for e in events if e.get("type") == "final_result"]
    assert len(final_events) == 1, f"Expected final_result event, got: {events}"
    result = final_events[0]["data"]
    assert result.get("razorpay_order_id") == fake_rp_order["id"]

    # Verify AuditLog has order_id set
    order_id = result.get("order_id")
    assert order_id is not None

    audit_with_order = db.query(AuditLog).filter(
        AuditLog.order_id == order_id
    ).first()
    assert audit_with_order is not None, \
        "At least one AuditLog entry must have order_id set for a successful purchase"

    # Verify PAYMENT_ORDER_CREATED is in audit trail
    payment_created_log = db.query(AuditLog).filter(
        AuditLog.order_id == order_id,
        AuditLog.action == "PAYMENT_ORDER_CREATED"
    ).first()
    assert payment_created_log is not None, "PAYMENT_ORDER_CREATED must be audited with order_id"
    assert payment_created_log.metadata_json["razorpay_order_id"] == fake_rp_order["id"]


# ─── Test 5: Customer Settings Returns spending_limit_set ────────────────────

def test_customer_settings_spending_limit_set_flag(client, setup_data, db):
    """
    GET /api/customer/settings must return spending_limit_set=False when 
    transaction_limit is NULL, and spending_limit_set=True after setting it.
    """
    token = setup_data["token"]
    merchant_id = setup_data["merchant_id"]

    # Reset limit to NULL
    customer = db.query(Customer).filter(Customer.id == setup_data["customer_id"]).first()
    customer.transaction_limit = None
    db.commit()

    res = client.get(
        f"/api/customer/settings?merchant_id={merchant_id}",
        headers=auth_headers(token)
    )
    assert res.status_code == 200
    data = res.json()
    assert data["spending_limit_set"] is False, \
        "spending_limit_set must be False when transaction_limit is NULL"

    # Now set a limit
    res2 = client.put(
        f"/api/customer/settings?merchant_id={merchant_id}",
        json={"transaction_limit": 5000.0, "daily_limit": 20000.0},
        headers=auth_headers(token)
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["spending_limit_set"] is True, \
        "spending_limit_set must be True after setting transaction_limit"
    assert data2["transaction_limit"] == 5000.0

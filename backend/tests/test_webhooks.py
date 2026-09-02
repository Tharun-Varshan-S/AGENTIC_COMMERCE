import pytest
import hmac
import hashlib
import json
import os
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import SessionLocal
from app.models.audit import AuditLog

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_webhook_tampered_body_rejected(db_session, monkeypatch):
    # Mock environment variables to ensure the razorpay client is active during the test
    # so we can test the actual utility signature logic
    monkeypatch.setenv("RAZORPAY_KEY_ID", "test_key_id")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "test_key_secret")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret")
    
    # We must reload razorpay_client or patch the `client` in the module
    import razorpay
    from app.payment import razorpay_client
    razorpay_client.client = razorpay.Client(auth=("test_key_id", "test_key_secret"))
    razorpay_client.RAZORPAY_WEBHOOK_SECRET = "test_webhook_secret"

    payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_123",
                    "order_id": "order_123"
                }
            }
        }
    }
    raw_body = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    
    tampered_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_123",
                    "order_id": "order_456" # malicious edit
                }
            }
        }
    }
    tampered_body = json.dumps(tampered_payload, separators=(',', ':')).encode('utf-8')

    # Compute signature using the valid body
    signature = hmac.new(b"test_webhook_secret", raw_body, hashlib.sha256).hexdigest()

    headers = {
        "X-Razorpay-Signature": signature,
        "Content-Type": "application/json"
    }

    initial_audit_count = db_session.query(AuditLog).filter_by(action="WEBHOOK_SIGNATURE_MISMATCH").count()

    response = client.post("/api/webhooks/razorpay", content=tampered_body, headers=headers)

    # Assert 400 Bad Request
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid signature"

    # Assert an AuditLog entry was created
    final_audit_count = db_session.query(AuditLog).filter_by(action="WEBHOOK_SIGNATURE_MISMATCH").count()
    assert final_audit_count == initial_audit_count + 1

    audit_entry = db_session.query(AuditLog).filter_by(action="WEBHOOK_SIGNATURE_MISMATCH").order_by(AuditLog.created_at.desc()).first()
    assert audit_entry.actor_type == "EXTERNAL"
    assert "error" in audit_entry.metadata_json

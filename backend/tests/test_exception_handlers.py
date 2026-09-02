import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
import logging

def test_raw_exception_does_not_leak_in_payments(caplog):
    # Instead of overriding DB which fails outside the try/except block, 
    # we mock verify_payment directly.
    # To bypass db.query returning 404, we mock get_db to return a mock DB
    # that returns a mock payment
    def mock_get_db_success():
        class MockPayment:
            id = "test"
            class MockOrder:
                customer_id = "test_customer"
            order = MockOrder()

        class MockQuery:
            def filter(self, *args, **kwargs):
                return self
            def first(self):
                return MockPayment()

        class MockSession:
            def query(self, *args, **kwargs):
                return MockQuery()
            def close(self):
                pass
        yield MockSession()

    app.dependency_overrides[get_db] = mock_get_db_success

    
    from unittest.mock import patch

    client = TestClient(app, raise_server_exceptions=False)
    
    with caplog.at_level(logging.ERROR):
        # We need to mock a function inside the try block of verify_payment_route
        with patch("app.api.payments.verify_payment", side_effect=Exception("RAW_DB_EXCEPTION_MESSAGE")):
            res = client.post("/api/payments/verify", json={
                "payment_id": "test",
                "razorpay_payment_id": "test",
                "razorpay_order_id": "test",
                "razorpay_signature": "test"
            })
    
    app.dependency_overrides.pop(get_db, None)
    
    # Should return 500
    assert res.status_code == 500
    
    body = res.text
    # Should not leak raw error to client
    assert "RAW_DB_EXCEPTION_MESSAGE" not in body
    # Should have clean generic message
    assert "An internal server error occurred." in body
    
    # Should log the exception server-side
    assert "Unexpected error in verify_payment_route" in caplog.text
    assert "RAW_DB_EXCEPTION_MESSAGE" in caplog.text

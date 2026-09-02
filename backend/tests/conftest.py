import pytest
from app.main import app
from app.api.auth import get_current_customer_user, get_current_merchant_user
from app.models.user import User
from app.models.merchant import Merchant
import uuid
from unittest.mock import patch

def mock_get_current_customer_user():
    return User(email="test@demo.com", role="CUSTOMER")

def mock_get_current_merchant_user():
    return Merchant(id=str(uuid.uuid4()), name="Test Merch", email="test@merch.com", is_active=True)

@pytest.fixture(autouse=True, scope="function")
def override_auth_dependencies(request):
    if "test_auth_enforcement" in request.module.__name__:
        app.dependency_overrides.pop(get_current_customer_user, None)
        app.dependency_overrides.pop(get_current_merchant_user, None)
        yield
    else:
        app.dependency_overrides[get_current_customer_user] = mock_get_current_customer_user
        app.dependency_overrides[get_current_merchant_user] = mock_get_current_merchant_user
        
        # Patch verify_customer_ownership to do nothing
        with patch('app.api.payments.verify_customer_ownership'), \
             patch('app.api.consent.verify_customer_ownership'), \
             patch('app.api.agent.verify_customer_ownership'):
            yield

    app.dependency_overrides.clear()

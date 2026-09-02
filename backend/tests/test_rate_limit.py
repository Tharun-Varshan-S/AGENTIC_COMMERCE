import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.merchant import Merchant
from app.models.customer import Customer
from app.models.agent import AgentDecision
import uuid
from app.models.user import User
from app.core.security import get_password_hash, create_access_token
from app.api.rate_limit import reset_rate_limits

client = TestClient(app)

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def rate_limit_setup(db_session):
    reset_rate_limits()
    
    m_id = str(uuid.uuid4())
    merchant = Merchant(id=m_id, name="Rate Limit Merchant", email=f"rl_{m_id}@m.com", is_active=True)
    db_session.add(merchant)

    u_id = str(uuid.uuid4())
    user = User(
        id=u_id,
        email=f"rl_{u_id}@m.com",
        hashed_password=get_password_hash("password"),
        role="MERCHANT_ADMIN",
        merchant_id=m_id,
        is_active=True
    )
    db_session.add(user)

    c_id = str(uuid.uuid4())
    customer = Customer(id=c_id, merchant_id=m_id, name="RL Cust", email=f"rl_{c_id}@c.com")
    db_session.add(customer)
    db_session.commit()

    token = create_access_token({"sub": user.email, "role": user.role})
    
    return {
        "merchant_id": m_id,
        "customer_id": c_id,
        "token": token
    }

def test_rate_limit_enforced_and_audited(db_session, rate_limit_setup):
    token = rate_limit_setup["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    initial_decisions = db_session.query(AgentDecision).filter_by(decision_status="THROTTLED").count()

    # Fire 5 requests (Limit is 5)
    for _ in range(5):
        res = client.get("/api/agent-catalog.json", headers=headers)
        assert res.status_code == 200

    # 6th request should fail with 429 Too Many Requests
    res = client.get("/api/agent-catalog.json", headers=headers)
    assert res.status_code == 429
    assert res.json()["detail"] == "Too Many Requests"

    # Assert AgentDecision row was inserted
    final_decisions = db_session.query(AgentDecision).filter_by(decision_status="THROTTLED").count()
    assert final_decisions == initial_decisions + 1
    
    decision = db_session.query(AgentDecision).filter_by(decision_status="THROTTLED").order_by(AgentDecision.created_at.desc()).first()
    assert decision.actor_type == "EXTERNAL"
    assert decision.action == "API_RATE_LIMIT"
    assert "/api/agent-catalog.json" in decision.scoring_details["path"]

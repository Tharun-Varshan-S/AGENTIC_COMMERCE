import time
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.agent import AgentDecision
from app.models.customer import Customer

# In-memory limiter is acceptable for a demo.
# Note: For production, use a Redis-backed token bucket or slowapi.
RATE_LIMIT = 5
RATE_LIMIT_WINDOW = 60 # seconds

_rate_limits = {}

def check_rate_limit(key: str, merchant_id: str, db: Session, customer_id: str = None, path: str = ""):
    current_time = time.time()
    
    record = _rate_limits.get(key)
    if not record or current_time - record["start_time"] > RATE_LIMIT_WINDOW:
        _rate_limits[key] = {"count": 1, "start_time": current_time}
        return
        
    if record["count"] >= RATE_LIMIT:
        if not customer_id:
            cust = db.query(Customer).filter_by(merchant_id=merchant_id).first()
            if cust:
                customer_id = str(cust.id)
                
        # If we still don't have a customer, we can't log to AgentDecision because customer_id is non-nullable.
        # We will log if we have it.
        if customer_id:
            decision = AgentDecision(
                merchant_id=merchant_id,
                customer_id=customer_id,
                actor_type="EXTERNAL",
                action="API_RATE_LIMIT",
                decision_status="THROTTLED",
                scoring_details={"key": key, "path": path}
            )
            db.add(decision)
            db.commit()
            
        raise HTTPException(status_code=429, detail="Too Many Requests")
        
    record["count"] += 1

def reset_rate_limits():
    """Useful for testing"""
    _rate_limits.clear()

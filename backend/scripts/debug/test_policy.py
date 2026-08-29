import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import engine, SessionLocal
from app.db.base import Base # This imports all models usually
from app.models.order import Cart
from app.policy.service import PolicyService
from app.policy.schemas import PolicyEvaluationRequest

db = SessionLocal()
try:
    req = PolicyEvaluationRequest(
        merchant_id="6ba7b810-9dad-11d1-80b4-00c04fd430c8", 
        customer_id="17f80b9c-2079-4f80-a7d3-2699d01d00f5",
        cart_id="a9f21c42-f798-4d34-9a2b-44f6e59e074d"
    )
    cart = db.query(Cart).filter(Cart.id == "a9f21c42-f798-4d34-9a2b-44f6e59e074d").first()
    if cart:
        req.merchant_id = str(cart.merchant_id)
        req.customer_id = str(cart.customer_id)
        print("Evaluating policy for cart", req.cart_id)
        service = PolicyService(db)
        decision = service.evaluate(req)
        print("Decision:", decision.model_dump_json(indent=2))
    else:
        print("Cart not found")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()

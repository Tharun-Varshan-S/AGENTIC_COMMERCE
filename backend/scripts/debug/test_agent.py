import os
import uuid
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.agent.schemas import ChatRequest
from app.agent.service import get_agent_response

def run():
    db = SessionLocal()
    try:
        req = ChatRequest(
            session_id=str(uuid.uuid4()),
            merchant_id="e224e772-e1d8-4f81-80cf-607be22f2f11", # seed merchant
            customer_id="b8393e03-a26a-4933-9110-3de5c957e847", # seed customer
            message="Find me a gaming mouse under 3000"
        )
        
        print("Calling agent...")
        resp = get_agent_response(req, db)
        print("Response message:", resp.message)
        for tc in resp.tool_calls:
            print(f"- Tool called: {tc.tool} (Reason: {tc.reason})")
            
        print("Products in state:", len(resp.products))
    finally:
        db.close()

if __name__ == "__main__":
    run()

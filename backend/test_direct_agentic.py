import asyncio
import httpx
import uuid
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from run_live_flows import setup_data
from app.db.session import SessionLocal
from app.models.agent import AgentDecision

API_URL = "http://localhost:8080"

async def test_direct_agentic():
    data = await setup_data()
    print("Setup Data:", data)
    
    async with httpx.AsyncClient(timeout=120) as client:
        # Trigger direct agentic payment
        print("\n--- Triggering direct agentic payment ---")
        res = await client.post(f"{API_URL}/api/payments/execute-direct-agentic", headers={"Authorization": f"Bearer {data['cust_token']}"}, json={
            "merchant_id": data["m_id"],
            "offer_id": data["o_laptop"],
            "quantity": 1
        })
        print(f"Status: {res.status_code}")
        print(f"Response: {res.json() if res.status_code == 200 else res.text}")
        
        db = SessionLocal()
        decisions = db.query(AgentDecision).filter_by(customer_id=data["c_id"]).all()
        print(f"Agent Decisions: {[d.policy_rules for d in decisions]}")
        db.close()

if __name__ == "__main__":
    asyncio.run(test_direct_agentic())

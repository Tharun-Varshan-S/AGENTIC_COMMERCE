import asyncio
import json
import sys
import os
from dotenv import load_dotenv
load_dotenv()

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
import app.db.base # Ensure all models are loaded
from app.agent.graph import build_graph
from langgraph.graph import StateGraph

async def main():
    print("Testing Agent Workflow...")
    app = build_graph()
    
    # Mock input state for a simple search query
    state = {
        "messages": [
            ("user", "Find me a gaming mouse under 3000 rupees")
        ],
        "shopping_intent": {
            "query": "gaming mouse",
            "is_search": True,
            "max_price": 3000
        },
        "customer_id": "test_customer",
        "merchant_id": "razorpay"
    }
    
    # We will just run the graph to see if the search pipeline succeeds 
    # and populates products without crashing.
    print("Invoking graph...")
    try:
        db = SessionLocal()
        config = {
            "configurable": {
                "thread_id": "test_thread",
                "db": db
            }
        }
        final_state = await app.ainvoke(state, config=config)
        
        products = final_state.get("products", [])
        print(f"Success! Found {len(products)} products.")
        if products:
            print("First product:", products[0].get("title", "No title"))
            
        # Check LLM response
        messages = final_state.get("messages", [])
        if messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                print("Agent Response:", last_msg.content)
            else:
                print("Agent Response:", last_msg)
            
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())

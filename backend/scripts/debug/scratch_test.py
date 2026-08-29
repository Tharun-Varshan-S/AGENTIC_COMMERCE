import sys
import asyncio
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from langchain_core.messages import HumanMessage
from app.agent.graph import build_graph

# Setup dummy DB
engine = create_engine("sqlite:///:memory:")

def test_graph():
    graph = build_graph()
    
    with Session(engine) as db_session:
        config = {
            "configurable": {
                "thread_id": "test_session_1",
                "db": db_session
            }
        }
        
        input_state = {
            "messages": [HumanMessage(content="I am looking for a laptop under $1000")],
            "session_id": "test_session_1",
            "merchant_id": "razorpay",
            "customer_id": "test_customer"
        }
        
        print("Running graph...")
        for event in graph.stream(input_state, config=config, stream_mode="updates"):
            print(event)

if __name__ == "__main__":
    test_graph()

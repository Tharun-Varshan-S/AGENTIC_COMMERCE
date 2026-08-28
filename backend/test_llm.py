import asyncio
from app.agent.graph import build_graph
from langchain_core.messages import HumanMessage

async def main():
    graph = build_graph()
    state = {"messages": [HumanMessage(content="Find me a gaming mouse under 3000 rupees. Please search across all available platforms and merchants to find the best options")]}
    res = await graph.ainvoke(state, config={"configurable": {"thread_id": "1", "db": None}})
    print("State shopping intent:", res.get("shopping_intent"))
    print("Normalized products:", len(res.get("normalized_products", [])))

asyncio.run(main())

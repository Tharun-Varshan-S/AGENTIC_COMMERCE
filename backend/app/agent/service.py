from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.orm import Session
import json

from app.agent.graph import build_graph
from app.agent.schemas import ChatRequest, ChatResponse, ToolCallLog

# Build the graph globally
agent_graph = build_graph()

def get_agent_response_stream(request: ChatRequest, db_session: Session):
    config = {
        "configurable": {
            "thread_id": request.session_id,
            "db": db_session
        }
    }
    
    input_state = {
        "messages": [HumanMessage(content=request.message)],
        "session_id": request.session_id,
        "merchant_id": request.merchant_id,
        "customer_id": request.customer_id
    }
    
    try:
        # Stream updates from the graph as they happen
        for update in agent_graph.stream(input_state, config=config, stream_mode="updates"):
            for node_name, state_update in update.items():
                event_data = {
                    "type": "orchestration",
                    "node": node_name,
                    "status": "completed"
                }
                
                # Extract tool calls from the agent node if present
                if node_name == "agent" and "messages" in state_update:
                    last_msg = state_update["messages"][-1]
                    if getattr(last_msg, "tool_calls", None):
                        event_data["tool_calls"] = last_msg.tool_calls
                        
                # Extract tool executions if present
                if node_name == "tools" and "messages" in state_update:
                    tool_results = []
                    for msg in state_update["messages"]:
                        if getattr(msg, "name", None):
                            tool_results.append({"tool": msg.name, "result": "completed"})
                    if tool_results:
                        event_data["tool_results"] = tool_results
                
                yield json.dumps(event_data) + "\n"
    except Exception as e:
        import traceback
        traceback.print_exc()
        yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        return

    # Once graph is done, get the final state
    full_state = agent_graph.get_state(config).values
    messages = full_state.get("messages", [])
    
    final_message = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            if isinstance(msg.content, str):
                final_message = msg.content
            elif isinstance(msg.content, list):
                texts = [block.get("text", "") if isinstance(block, dict) else str(block) for block in msg.content]
                final_message = "\n".join(texts)
            break
            
    tool_calls_log = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            break
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in reversed(msg.tool_calls):
                args = tc.get("args", {})
                reason = args.get("reason", "No reason provided.")
                tool_calls_log.insert(0, ToolCallLog(tool=tc["name"], reason=reason).model_dump())
                
    response_data = {
        "session_id": request.session_id,
        "message": final_message,
        "tool_calls": tool_calls_log,
        "products": full_state.get("products", []),
        "comparison": full_state.get("comparison"),
        "ranked_products": full_state.get("ranked_products"),
        "recommendation": full_state.get("recommendation"),
        "cart": full_state.get("cart"),
        "checkout_session": full_state.get("checkout_session"),
        "policy": full_state.get("policy"),
        "requires_consent": full_state.get("requires_consent", False),
        "payment_order": full_state.get("payment_order")
    }
    
    yield json.dumps({"type": "final_result", "data": response_data}) + "\n"


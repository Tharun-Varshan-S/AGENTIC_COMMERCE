from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.orm import Session
import json

from app.agent.graph import build_graph
from app.agent.schemas import ChatRequest, ChatResponse, ToolCallLog

# Build the graph globally
agent_graph = build_graph()

def get_agent_response(request: ChatRequest, db_session: Session) -> ChatResponse:
    config = {
        "configurable": {
            "thread_id": request.session_id,
            "db": db_session
        }
    }
    
    # Initialize the input state with the new human message
    input_state = {
        "messages": [HumanMessage(content=request.message)],
        "session_id": request.session_id,
        "merchant_id": request.merchant_id,
        "customer_id": request.customer_id
    }
    
    # Invoke the graph. The MemorySaver will automatically fetch previous messages
    # for this thread_id, append the new input_state message, and run the agent.
    result_state = agent_graph.invoke(input_state, config=config)
    
    # Extract the response
    messages = result_state.get("messages", [])
    
    # Find the last AIMessage content that is not just a tool call
    final_message = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            final_message = msg.content
            break
            
    # Extract tool logs for the CURRENT turn only (to return in the API response)
    # Actually, the user wants the tool calls that happened in this request.
    # To differentiate, we can look at the messages added in this invocation.
    # But for simplicity, we can just grab all tool calls or just the most recent sequence.
    # Let's extract from the last few messages until we hit a HumanMessage.
    
    tool_calls_log = []
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            break
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            # Because we're iterating backwards, we should insert at the beginning
            # to maintain chronological order
            for tc in reversed(msg.tool_calls):
                args = tc.get("args", {})
                reason = args.get("reason", "No reason provided.")
                tool_calls_log.insert(0, ToolCallLog(tool=tc["name"], reason=reason))
                
    return ChatResponse(
        session_id=request.session_id,
        message=final_message,
        tool_calls=tool_calls_log,
        products=result_state.get("products", []),
        recommendation=result_state.get("recommendation"),
        cart=result_state.get("cart"),
        policy=result_state.get("policy"),
        requires_consent=result_state.get("requires_consent", False)
    )

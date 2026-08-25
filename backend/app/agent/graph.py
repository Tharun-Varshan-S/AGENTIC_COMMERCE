import json
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import ToolMessage, SystemMessage, AIMessage
from langchain_core.runnables import RunnableConfig

from app.agent.schemas import AgentState
from app.agent.llm import get_llm
from app.agent.tools import create_agent_tools
from app.agent.prompts import SYSTEM_PROMPT

MAX_TOOL_CALLS = 8

def agent_node(state: AgentState, config: RunnableConfig):
    # Initialize tools and model
    tools = create_agent_tools()
    llm = get_llm().bind_tools(tools)
    
    # Ensure system prompt is first
    messages = state.get("messages", [])
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
    # Check max tool calls
    if state.get("tool_call_count", 0) >= MAX_TOOL_CALLS:
        return {"messages": [AIMessage(content="I wasn't able to fully resolve this — could you clarify what you're looking for?")]}
        
    response = llm.invoke(messages)
    return {"messages": [response]}

def tools_node(state: AgentState, config: RunnableConfig):
    last_message = state["messages"][-1]
    tools = {t.name: t for t in create_agent_tools()}
    
    tool_messages = []
    state_updates = {"tool_call_count": state.get("tool_call_count", 0) + 1}
    
    for tool_call in getattr(last_message, "tool_calls", []):
        tool = tools.get(tool_call["name"])
        if not tool:
            tool_messages.append(ToolMessage(
                content=f"Error: Tool {tool_call['name']} not found.",
                tool_call_id=tool_call["id"]
            ))
            continue
            
        try:
            # Execute tool directly to capture object return
            output = tool.invoke(tool_call["args"], config=config)
            
            # The tool adapter returns {"result": ..., "reason": ...}
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except:
                    pass
                    
            if isinstance(output, dict) and "result" in output:
                result = output["result"]
            else:
                result = output
                
            # Update UI state based on tool name
            name = tool_call["name"]
            if name == "search_catalog":
                state_updates["products"] = result.get("products", []) if isinstance(result, dict) else []
            elif name == "get_product":
                if isinstance(result, dict) and "error" not in result:
                    state_updates["products"] = [result]
            elif name == "get_revenue_recommendation":
                state_updates["recommendation"] = result
            elif name in ["calculate_cart", "add_to_cart", "remove_from_cart", "update_cart_quantity"]:
                state_updates["cart"] = result
            elif name == "validate_policy":
                state_updates["policy"] = result
                state_updates["requires_consent"] = result.get("requires_consent", False) if isinstance(result, dict) else False
            elif name == "create_razorpay_order":
                if isinstance(result, dict) and "error" not in result:
                    state_updates["payment_order"] = result
                
            # Convert full output (including reason) to string for the LLM
            content = json.dumps(output)
            
            tool_messages.append(ToolMessage(
                content=content,
                tool_call_id=tool_call["id"]
            ))
        except Exception as e:
            tool_messages.append(ToolMessage(
                content=f"Error executing tool: {str(e)}",
                tool_call_id=tool_call["id"]
            ))
            
    state_updates["messages"] = tool_messages
    return state_updates

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state.get("messages", [])
    if not messages:
        return "__end__"
        
    last_message = messages[-1]
    
    # Check if there are tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # Check loop limit
        if state.get("tool_call_count", 0) >= MAX_TOOL_CALLS:
            return "__end__"
        return "tools"
    return "__end__"

def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

import json
from typing import Literal

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import ToolMessage, SystemMessage, AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agent.schemas import AgentState
from app.agent.llm import get_llm
from app.agent.tools import create_agent_tools
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.models import ShoppingIntent
from app.agent.merchants import get_available_merchants

MAX_TOOL_CALLS = 8

def plan_node(state: AgentState, config: RunnableConfig):
    """Parses user input into a structured ShoppingIntent if applicable."""
    messages = state.get("messages", [])
    if not messages:
        return {}
        
    last_msg = messages[-1]
    if not isinstance(last_msg, HumanMessage):
        # We only plan on new human messages
        return {}
        
    llm = get_llm()
    structured_llm = llm.with_structured_output(ShoppingIntent)
    
    intent = structured_llm.invoke([
        SystemMessage(content="You are a shopping assistant planner. Extract the user's shopping intent. If the user is just saying hello or asking a general question, set is_search to false."),
        last_msg
    ])
    return {"shopping_intent": intent.model_dump()}

def discover_node(state: AgentState, config: RunnableConfig):
    """Finds all capabilities and merchants available."""
    intent = state.get("shopping_intent")
    if not intent or not intent.get("is_search"):
        return {}
        
    merchants = get_available_merchants()
    return {"discovered_merchants": [m.source_id for m in merchants]}

def search_node(state: AgentState, config: RunnableConfig):
    """Executes parallel searches across discovered merchants."""
    intent = state.get("shopping_intent")
    merchant_ids = state.get("discovered_merchants", [])
    
    if not intent or not intent.get("is_search") or not merchant_ids:
        return {}
        
    db_session = config["configurable"]["db"]
    merchants = get_available_merchants()
    
    all_products = []
    for m in merchants:
        if m.source_id in merchant_ids:
            try:
                products = m.search_catalog(
                    db_session=db_session,
                    query=intent.get("query", ""),
                    category=intent.get("keywords", [])[0] if intent.get("keywords") else None,
                    max_price=intent.get("max_price"),
                    limit=5
                )
                all_products.extend([p.model_dump() for p in products])
            except Exception as e:
                print(f"Error searching merchant {m.name}: {e}")
                
    return {"normalized_products": all_products}

def rank_node(state: AgentState, config: RunnableConfig):
    """Ranks and formats normalized products into the state format expected by the frontend."""
    products = state.get("normalized_products", [])
    if not products:
        return {}
    
    ui_products = []
    for p in products[:10]:
        ui_products.append({
            "id": p["id"],
            "offer_id": p.get("offer_id"),
            "source": p.get("merchant", "local_db"),
            "name": p["title"],
            "price": p["price"],
            "image_url": p.get("url"),
            "description": p["description"],
            "delivery_estimate": p.get("delivery_estimate")
        })
        
    return {"products": ui_products}


def agent_node(state: AgentState, config: RunnableConfig):
    """Main conversational agent that responds to the user and orchestrates tool usage."""
    tools = create_agent_tools()
    llm = get_llm().bind_tools(tools)
    
    messages = list(state.get("messages", []))
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
    # Inject context from pipeline if we did a search
    intent = state.get("shopping_intent")
    if intent and intent.get("is_search"):
        products = state.get("products", [])
        if products:
            context_msg = f"Search Results Context: The search pipeline was executed. Found {len(products)} products across merchants based on your plan. Summarize these briefly to the user. Results: {json.dumps(products)}"
        else:
            context_msg = "Search Results Context: The search pipeline was executed but NO products were found in the catalog matching the user's criteria. Inform the user that no products were found and ask them to adjust their search terms or budget. DO NOT attempt to search manually using tools."
        messages.append(SystemMessage(content=context_msg))
        
    # Inject auth context
    from app.payment.agentic_service import get_active_authorization
    db = config.get("configurable", {}).get("db")
    customer_id = config.get("configurable", {}).get("customer_id")
    if db and customer_id:
        auth = get_active_authorization(db, customer_id)
        if auth:
            auth_msg = f"User has an active Agentic Payment capability (Rail: {auth.rail}). Per transaction limit: {auth.per_transaction_limit}. Remaining daily limit: {auth.daily_limit - auth.spent_today}. You can execute payments autonomously if within this limit by asking for their approval and then using execute_agentic_payment."
            messages.append(SystemMessage(content=auth_msg))
            
    # Check max tool calls
    if state.get("tool_call_count", 0) >= MAX_TOOL_CALLS:
        return {"messages": [AIMessage(content="I wasn't able to fully resolve this — could you clarify what you're looking for?")]}
        
    try:
        response = llm.invoke(messages)
        return {"messages": [response]}
    except Exception as e:
        import traceback
        traceback.print_exc()
        error_msg = str(e).lower()
        if "429" in error_msg or "resource_exhausted" in error_msg or "quota" in error_msg:
            return {"messages": [AIMessage(content="The AI agent is temporarily unavailable because the Gemini API quota has been exhausted. Please retry after a few moments.")]}
        return {"messages": [AIMessage(content=f"An unexpected error occurred during agent execution: {str(e)}")]}

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
            output = tool.invoke(tool_call["args"], config=config)
            
            if isinstance(output, str):
                try:
                    output = json.loads(output)
                except:
                    pass
                    
            if isinstance(output, dict) and "result" in output:
                result = output["result"]
            else:
                result = output
                
            name = tool_call["name"]
            if name in ["search_amazon_catalog", "search_flipkart_catalog", "search_razorpay_merchants", "search_catalog"]:
                current_products = state.get("products", []) or []
                new_products = result.get("products", []) if isinstance(result, dict) else []
                state_updates["products"] = current_products + new_products
            elif name == "get_product_details":
                if isinstance(result, dict) and "error" not in result:
                    state_updates["products"] = [result]
            elif name == "compare_products":
                state_updates["comparison"] = result.get("comparison", []) if isinstance(result, dict) else []
            elif name == "rank_products":
                state_updates["ranked_products"] = result.get("ranked_products", []) if isinstance(result, dict) else []
            elif name == "create_checkout_session":
                if isinstance(result, dict) and result.get("checkout_ready"):
                    state_updates["checkout_session"] = result
            elif name == "get_revenue_recommendation":
                state_updates["recommendation"] = result
            elif name in ["calculate_cart", "add_to_cart", "remove_from_cart", "update_cart_quantity"]:
                state_updates["cart"] = result
            elif name == "validate_policy":
                state_updates["policy"] = result
                state_updates["requires_consent"] = result.get("requires_consent", False) if isinstance(result, dict) else False
            elif name == "execute_agentic_payment":
                state_updates["checkout_session"] = {"checkout_ready": False, "agentic_paid": True}
                
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

def should_search(state: AgentState) -> Literal["discover", "agent"]:
    intent = state.get("shopping_intent")
    if intent and intent.get("is_search"):
        return "discover"
    return "agent"

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    messages = state.get("messages", [])
    if not messages:
        return "__end__"
        
    last_message = messages[-1]
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        if state.get("tool_call_count", 0) >= MAX_TOOL_CALLS:
            return "__end__"
        return "tools"
    return "__end__"

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("plan", plan_node)
    workflow.add_node("discover", discover_node)
    workflow.add_node("search", search_node)
    workflow.add_node("rank", rank_node)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    
    workflow.add_edge(START, "plan")
    workflow.add_conditional_edges("plan", should_search)
    workflow.add_edge("discover", "search")
    workflow.add_edge("search", "rank")
    workflow.add_edge("rank", "agent")
    
    # After agent decides, it can either end or call tools
    workflow.add_conditional_edges("agent", should_continue)
    workflow.add_edge("tools", "agent")
    
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)

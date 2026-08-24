from typing import TypedDict, Annotated, List, Optional, Any, Dict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    """LangGraph State for the AI Agent."""
    messages: Annotated[list[BaseMessage], add_messages]
    session_id: str
    merchant_id: str
    customer_id: str
    tool_call_count: int
    
    # UI state variables collected by intercepting tools
    products: Optional[List[Dict[str, Any]]]
    recommendation: Optional[Dict[str, Any]]
    cart: Optional[Dict[str, Any]]
    policy: Optional[Dict[str, Any]]
    requires_consent: bool

class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique session ID for the conversation")
    merchant_id: str = Field(..., description="The merchant ID")
    customer_id: str = Field(..., description="The customer ID")
    message: str = Field(..., description="The user's text message")

class ToolCallLog(BaseModel):
    tool: str = Field(..., description="The name of the tool called")
    reason: str = Field(..., description="A short, one-line LLM-generated reason for why this tool was called")

class ChatResponse(BaseModel):
    session_id: str = Field(..., description="Unique session ID")
    message: str = Field(..., description="The final AI assistant response text")
    tool_calls: List[ToolCallLog] = Field(default_factory=list, description="List of tools executed with their reasons")
    
    # UI state variables
    products: List[Dict[str, Any]] = Field(default_factory=list)
    recommendation: Optional[Dict[str, Any]] = None
    cart: Optional[Dict[str, Any]] = None
    policy: Optional[Dict[str, Any]] = None
    requires_consent: bool = False

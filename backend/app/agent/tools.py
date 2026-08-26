from typing import List, Type, Dict, Any
from pydantic import BaseModel, Field, create_model
from langchain_core.tools import StructuredTool
from langchain_core.runnables import RunnableConfig

from app.tools import registry
from app.tools.base import CommerceTool

def create_agent_tools() -> List[StructuredTool]:
    """
    Dynamically wrap all tools from the Commerce ToolRegistry into LangChain StructuredTools.
    Adds a `reason` field to every tool schema to satisfy the reasoning trace requirement.
    """
    langchain_tools = []
    
    for tool in registry._tools.values():
        langchain_tools.append(_adapt_tool(tool))
        
    return langchain_tools

def _adapt_tool(commerce_tool: CommerceTool) -> StructuredTool:
    """Wraps a single CommerceTool into a LangChain StructuredTool."""
    
    # Dynamically inject the 'reason' field into the existing tool's Pydantic schema
    original_schema = commerce_tool.input_schema
    fields = {}
    for field_name, field_info in original_schema.model_fields.items():
        fields[field_name] = (field_info.annotation, field_info)
        
    fields["reason"] = (str, Field(..., description="Short, single-sentence reason for why you are executing this tool."))
    
    # Create the new schema with the reason field
    enhanced_schema = create_model(
        f"{commerce_tool.name.capitalize()}EnhancedSchema",
        **fields,
        __base__=BaseModel
    )

    def tool_func(*args, config: RunnableConfig, **kwargs) -> Any:
        db = config.get("configurable", {}).get("db")
        if not db:
            raise RuntimeError("Database session not found in RunnableConfig. Ensure you pass 'db' via config.")
            
        # The LLM will provide 'reason', but we don't pass it to the commerce tool logic.
        reason = kwargs.pop("reason", "No reason provided.")
        
        # We can also extract session_id, merchant_id, customer_id from config if needed
        # but typically the LLM passes required parameters.
        
        # Execute the commerce tool
        result = commerce_tool.execute(db_session=db, **kwargs)
        
        if hasattr(result, "model_dump"):
            dumped_result = result.model_dump()
        else:
            dumped_result = result
            
        return {
            "result": dumped_result,
            "reason": reason
        }

    return StructuredTool.from_function(
        func=tool_func,
        name=commerce_tool.name,
        description=commerce_tool.description,
        args_schema=enhanced_schema
    )

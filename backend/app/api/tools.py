from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.db.session import get_db
from app.tools import registry

router = APIRouter(prefix="/tools", tags=["Commerce Tools"])

@router.get("")
def list_tools():
    """
    Discovery endpoint listing all registered tools and their metadata.
    """
    return {
        "tools": registry.list_tools()
    }

@router.post("/{tool_name}/execute")
async def execute_tool(tool_name: str, request: Request, db: Session = Depends(get_db)):
    """
    Execute a specific commerce tool.
    """
    try:
        input_data = await request.json()
    except Exception:
        input_data = {}

    result = registry.execute(tool_name, input_data, db)
    
    # We return HTTP 200 even for tool-level errors (like INVALID_INPUT or NOT_FOUND) 
    # as per standard GraphQL/Agent patterns, the tool executed successfully and returned a structured error.
    # However, if the tool doesn't exist at all, we could return 404, but for consistency we return the structured tool result.
    return result.model_dump()

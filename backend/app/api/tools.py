from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.tools import registry
from app.api.auth import get_current_user, verify_customer_ownership, resolve_customer
from app.models.user import User

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
async def execute_tool(tool_name: str, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Execute a specific commerce tool.
    """
    try:
        input_data = await request.json()
    except Exception:
        input_data = {}

    merchant_id = input_data.get("merchant_id")
    customer_id = input_data.get("customer_id")
    
    if merchant_id:
        customer = resolve_customer(db, current_user, merchant_id, customer_id)
        input_data["customer_id"] = str(customer.id)
    elif customer_id:
        verify_customer_ownership(db, customer_id, current_user)

    try:
        result = registry.execute(tool_name, input_data, db)
    except Exception as e:
        logger.exception("Unexpected error in execute_tool")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    
    # We return HTTP 200 even for tool-level errors (like INVALID_INPUT or NOT_FOUND) 
    # as per standard GraphQL/Agent patterns, the tool executed successfully and returned a structured error.
    # However, if the tool doesn't exist at all, we could return 404, but for consistency we return the structured tool result.
    return result.model_dump()

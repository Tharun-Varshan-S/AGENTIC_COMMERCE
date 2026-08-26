from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.models.agent import AgentDecision
from app.schemas.agent import AgentDecisionResponse
from app.services.core import CoreService

from app.agent.schemas import ChatRequest, ChatResponse
from app.agent.service import get_agent_response

router = APIRouter()

def get_core_service(db: Session = Depends(get_db)) -> CoreService:
    return CoreService(db)

@router.get("/agent-decisions", response_model=List[AgentDecisionResponse])
def get_agent_decisions(
    customer_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    core_service: CoreService = Depends(get_core_service)
):
    query = select(AgentDecision)
    if customer_id:
        query = query.filter(AgentDecision.customer_id == customer_id)
        
    # We want to show the latest decisions
    query = query.order_by(AgentDecision.created_at.desc()).limit(10)
    
    decisions = db.scalars(query).all()
    
    results = []
    for d in decisions:
        resp = AgentDecisionResponse.model_validate(d)
        if d.primary_product_id:
            resp.primary_product = core_service.get_product(d.primary_product_id)
        if d.recommended_product_id:
            resp.recommended_product = core_service.get_product(d.recommended_product_id)
        results.append(resp)
        
    return results

from fastapi.responses import StreamingResponse
from app.agent.service import get_agent_response_stream

@router.post("/chat")
def chat_with_agent(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Interact with the autonomous AI Commerce Agent (Streaming).
    """
    return StreamingResponse(get_agent_response_stream(request, db), media_type="application/x-ndjson")


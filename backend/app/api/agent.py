from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.models.agent import AgentDecision
from app.schemas.agent import AgentDecisionResponse
from app.services.core import CoreService

from app.agent.schemas import ChatRequest, ChatResponse
from app.schemas.agent import AgentDecisionResponse, UpsellResponseRequest
from app.models.order import Cart, CartItem
from app.models.offer import Offer
from app.api.auth import get_current_customer_user, verify_customer_ownership, resolve_customer
from app.models.user import User

router = APIRouter()

def get_core_service(db: Session = Depends(get_db)) -> CoreService:
    return CoreService(db)

@router.get("/agent-decisions", response_model=List[AgentDecisionResponse])
def get_agent_decisions(
    merchant_id: str,
    customer_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    core_service: CoreService = Depends(get_core_service),
    current_user: User = Depends(get_current_customer_user)
):
    customer = resolve_customer(db, current_user, merchant_id, str(customer_id) if customer_id else None)
    
    query = select(AgentDecision)
    query = query.filter(AgentDecision.customer_id == customer.id)
        
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
    fastapi_req: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """
    Interact with the autonomous AI Commerce Agent (Streaming).
    """
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    request.customer_id = str(customer.id)
    from app.api.rate_limit import check_rate_limit
    key = fastapi_req.client.host if fastapi_req.client else "unknown"
    auth = fastapi_req.headers.get("Authorization")
    if auth: key = auth
    check_rate_limit(key, request.merchant_id, db, customer_id=request.customer_id, path=fastapi_req.url.path)
    
    return StreamingResponse(get_agent_response_stream(request, db), media_type="application/x-ndjson")

@router.post("/upsell/response")
def handle_upsell_response(
    request: UpsellResponseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    customer = resolve_customer(db, current_user, str(request.merchant_id), str(request.customer_id) if request.customer_id else None)
    request.customer_id = customer.id
    
    # 1. Verify Cart
    cart = db.query(Cart).filter(Cart.id == request.cart_id, Cart.customer_id == request.customer_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
        
    offer = db.query(Offer).filter(Offer.id == request.offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    decision = AgentDecision(
        customer_id=request.customer_id,
        merchant_id=request.merchant_id,
        decision_type="upsell_response",
        recommended_product_id=offer.product_id,
        actor_type="USER"
    )

    if request.action.lower() == "accept":
        # Add to cart
        existing_item = db.query(CartItem).filter(CartItem.cart_id == cart.id, CartItem.offer_id == offer.id).first()
        if existing_item:
            existing_item.quantity += 1
        else:
            item = CartItem(
                cart_id=cart.id,
                offer_id=offer.id,
                quantity=1,
                unit_price=offer.price
            )
            db.add(item)
            
        decision.action = "UPSELL_ACCEPTED"
        decision.decision_status = "ACCEPTED"
    else:
        decision.action = "UPSELL_DECLINED"
        decision.decision_status = "DECLINED"

    db.add(decision)
    db.commit()
    
    return {"status": "success"}

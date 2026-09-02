from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.api.auth import get_merchant_api_key_or_user
from app.models.merchant import Merchant
from app.models.product import Product, Inventory
from app.models.offer import Offer
from app.models.order import Cart, CartItem
from app.models.agent import AgentDecision
from app.policy.service import PolicyService
from app.policy.schemas import PolicyEvaluationRequest
from app.payment.agentic_service import execute_agentic_payment
from app.payment.exceptions import PaymentStateError
from app.api.rate_limit import check_rate_limit

router = APIRouter()

class CatalogProductResponse(BaseModel):
    id: str
    name: str
    description: str | None
    price: str  # String for precise decimal representation
    currency: str
    inventory: int
    checkout_intent_url: str
    offer_id: str

class CheckoutIntentRequest(BaseModel):
    merchant_id: str
    offer_id: str
    quantity: int
    requesting_agent_id: str
    customer_id: str

class CheckoutIntentResponse(BaseModel):
    status: str
    token: str
    confirm_url: str

class ConfirmCheckoutIntentResponse(BaseModel):
    status: str
    payment_id: str
    order_number: str
    amount: str
    message: str

@router.get("/agent-catalog.json", response_model=List[CatalogProductResponse])
def get_agent_catalog(
    request: Request,
    merchant: Merchant = Depends(get_merchant_api_key_or_user),
    db: Session = Depends(get_db)
):
    key = request.client.host if request.client else "unknown"
    auth = request.headers.get("Authorization")
    if auth: key = auth
    check_rate_limit(key, str(merchant.id), db, path=request.url.path)
    
    # Fetch active products, their offers and inventory
    # Assuming one offer per product for this MVP
    offers = db.query(Offer).filter(Offer.merchant_id == merchant.id).all()
    
    catalog = []
    for offer in offers:
        product = offer.product
        inventory = offer.inventory
        
        if not product or not inventory:
            continue
            
        catalog.append(
            CatalogProductResponse(
                id=str(product.id),
                name=product.name,
                description=product.description,
                price=str(offer.price),
                currency="INR",
                inventory=inventory.quantity,
                checkout_intent_url="/api/agent/checkout-intent",
                offer_id=str(offer.id)
            )
        )
    return catalog

@router.post("/agent/checkout-intent", response_model=CheckoutIntentResponse)
def create_checkout_intent(
    req: CheckoutIntentRequest,
    request: Request,
    merchant: Merchant = Depends(get_merchant_api_key_or_user),
    db: Session = Depends(get_db)
):
    if str(merchant.id) != req.merchant_id:
        raise HTTPException(status_code=403, detail="Merchant ID mismatch")
        
    key = request.client.host if request.client else "unknown"
    auth = request.headers.get("Authorization")
    if auth: key = auth
    check_rate_limit(key, req.merchant_id, db, customer_id=req.customer_id, path=request.url.path)

    offer = db.query(Offer).filter(Offer.id == req.offer_id, Offer.merchant_id == merchant.id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
        
    # 1. Create an ephemeral Cart for the checkout intent
    cart = Cart(
        customer_id=req.customer_id,
        merchant_id=req.merchant_id,
        status="ACTIVE",
        currency="INR",
        discount=Decimal('0')
    )
    db.add(cart)
    db.flush()
    
    # 2. Add CartItem
    item = CartItem(
        cart_id=cart.id,
        offer_id=offer.id,
        quantity=req.quantity,
        unit_price=offer.price
    )
    db.add(item)
    db.flush()
    
    # 3. Policy Engine Checks (checks inventory, price, spend limits, etc.)
    policy_service = PolicyService(db)
    policy_req = PolicyEvaluationRequest(
        merchant_id=req.merchant_id,
        customer_id=req.customer_id,
        cart_id=str(cart.id)
    )
    decision = policy_service.evaluate(policy_req).model_dump()
    
    # 4. Write AgentDecision for EXTERNAL_AGENT
    agent_decision = AgentDecision(
        customer_id=req.customer_id,
        merchant_id=req.merchant_id,
        action="CHECKOUT_INTENT_CREATION",
        actor_type="EXTERNAL_AGENT",
        decision_status=decision["decision"],
        policy_rules=decision["reasons"],
        primary_product_id=offer.product_id,
        scoring_details={"requesting_agent_id": req.requesting_agent_id}
    )
    db.add(agent_decision)
    db.commit()
    
    if decision["decision"] == "REJECTED":
        raise HTTPException(status_code=400, detail=f"Checkout rejected: {decision['reasons']}")
        
    # Return pending approval
    token = str(cart.id)
    return CheckoutIntentResponse(
        status="pending_approval",
        token=token,
        confirm_url=f"/api/agent/checkout-intent/{token}/confirm"
    )

@router.post("/agent/checkout-intent/{token}/confirm", response_model=ConfirmCheckoutIntentResponse)
def confirm_checkout_intent(
    token: str,
    merchant: Merchant = Depends(get_merchant_api_key_or_user),
    db: Session = Depends(get_db)
):
    cart = db.query(Cart).filter(Cart.id == token, Cart.merchant_id == merchant.id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Checkout intent token not found")
        
    try:
        res = execute_agentic_payment(
            db=db,
            merchant_id=str(merchant.id),
            customer_id=str(cart.customer_id),
            cart_id=str(cart.id)
        )
        return ConfirmCheckoutIntentResponse(
            status=res["status"],
            payment_id=res["payment_id"],
            order_number=res["order_number"],
            amount=res["amount"],
            message=res["message"]
        )
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

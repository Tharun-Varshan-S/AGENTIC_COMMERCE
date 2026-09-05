from fastapi import APIRouter, Depends, Query, Request, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import json
import asyncio

from app.db.session import get_db
from app.models.agent import AgentDecision
from app.schemas.agent import AgentDecisionResponse
from app.services.core import CoreService

from app.agent.schemas import ChatRequest, ChatResponse
from app.schemas.agent import AgentDecisionResponse, UpsellResponseRequest
from pydantic import BaseModel
from app.models.order import Cart, CartItem, Order
from app.models.offer import Offer
from app.api.auth import get_current_customer_user, verify_customer_ownership, resolve_customer
from app.models.user import User
from app.agent.service import get_agent_response_stream

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


class ExecutePurchaseRequest(BaseModel):
    merchant_id: str
    customer_id: Optional[str] = None
    type: str  # "buy_now" or "cart"
    product_id: Optional[str] = None
    offer_id: Optional[str] = None
    quantity: Optional[int] = 1
    cart_id: Optional[str] = None
    human_approval: bool = True


def _execute_purchase_stream(request: ExecutePurchaseRequest, customer_id: str, db: Session, current_user=None):
    """
    Generator that yields NDJSON step events while executing the purchase.
    This drives the real-time UI progress panel.

    Flow:
      LIMIT_CHECK → MERCHANT_CHECK → ORDER_CREATING → HEADLESS_CHARGE (if token exists)
                                                     → PAYMENT_READY (fallback: Checkout.js)
    """
    from app.payment.service import create_payment_order, create_direct_payment_order, charge_headless
    from app.payment.schemas import DirectCheckoutRequest
    from app.payment.exceptions import (
        PaymentStateError, TransactionLimitExceeded, DailyLimitExceeded,
        SpendingLimitNotConfigured, MerchantInactive, AgentAuthorizationError,
        RazorpayProviderError, InsufficientInventory,
        SavedInstrumentInvalid, ChargeDeclined
    )
    from app.models.customer import Customer
    from app.models.order import Payment

    def emit(step: str, status: str, detail: str = "", metadata: dict = None):
        event = {"type": "step", "step": step, "status": status, "detail": detail}
        if metadata:
            event["metadata"] = metadata
        return json.dumps(event) + "\n"

    try:
        # STEP 1: Validate spending limit is configured
        yield emit("LIMIT_CHECK", "running", "Checking spending limit configuration...")
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if customer is None or customer.transaction_limit is None:
            yield emit("LIMIT_CHECK", "blocked",
                       "No spending limit set. Please configure a limit in your profile.",
                       {"error_class": "SpendingLimitNotConfigured"})
            yield json.dumps({"type": "error", "error_class": "SpendingLimitNotConfigured",
                              "message": "No spending limit configured. Please set a per-transaction limit in your profile."}) + "\n"
            return

        tx_limit = float(customer.transaction_limit)
        daily_limit = float(customer.daily_limit) if customer.daily_limit is not None else 50000.0
        yield emit("LIMIT_CHECK", "passed",
                   f"Limit configured (₹{tx_limit:,.0f}/txn, ₹{daily_limit:,.0f}/day)",
                   {"tx_limit": tx_limit, "daily_limit": daily_limit})

        # STEP 2: Merchant verification
        yield emit("MERCHANT_CHECK", "running", "Verifying merchant...")
        from app.models.merchant import Merchant
        merchant = db.query(Merchant).filter(Merchant.id == request.merchant_id).first()
        if not merchant or not merchant.is_active:
            yield emit("MERCHANT_CHECK", "blocked", "Merchant not found or inactive.")
            yield json.dumps({"type": "error", "error_class": "MerchantInactive",
                              "message": "Merchant not found or inactive."}) + "\n"
            return
        yield emit("MERCHANT_CHECK", "passed", f"Merchant '{merchant.name}' verified")

        # STEP 3: Create Razorpay order
        yield emit("ORDER_CREATING", "running", "Creating order and checking inventory...")

        if request.type == "buy_now":
            if not request.product_id or not request.offer_id:
                yield emit("ORDER_CREATING", "blocked", "product_id and offer_id are required for buy_now")
                yield json.dumps({"type": "error", "error_class": "ValidationError",
                                  "message": "product_id and offer_id are required for buy_now"}) + "\n"
                return

            req = DirectCheckoutRequest(
                merchant_id=request.merchant_id,
                customer_id=customer_id,
                product_id=request.product_id,
                offer_id=request.offer_id,
                quantity=request.quantity or 1,
                source="DIRECT",
                agent_trace={"tool": "direct_ui_execution"},
                human_approval=True
            )
            res = create_direct_payment_order(db, req)

        elif request.type == "cart":
            if not request.cart_id:
                yield emit("ORDER_CREATING", "blocked", "cart_id is required for cart purchase")
                yield json.dumps({"type": "error", "error_class": "ValidationError",
                                  "message": "cart_id is required for cart purchase"}) + "\n"
                return

            res = create_payment_order(
                db=db,
                merchant_id=request.merchant_id,
                customer_id=customer_id,
                cart_id=request.cart_id,
                source="CART",
                agent_trace={"tool": "direct_ui_execution"},
                human_approval=True
            )
        else:
            yield emit("ORDER_CREATING", "blocked", f"Invalid purchase type: {request.type}")
            yield json.dumps({"type": "error", "error_class": "ValidationError",
                              "message": f"Invalid purchase type: {request.type}"}) + "\n"
            return

        yield emit("ORDER_CREATING", "passed",
                   f"Order {res.get('order_number')} created",
                   {"order_number": res.get("order_number"), "razorpay_order_id": res.get("razorpay_order_id")})

        # STEP 4: Try headless S2S charge if user has a saved instrument
        token_id = getattr(current_user, "active_mandate_token", None) if current_user else None
        rz_customer_id = getattr(current_user, "razorpay_customer_id", None) if current_user else None

        if token_id and rz_customer_id:
            yield emit("HEADLESS_CHARGE", "running",
                       f"Agent charging saved instrument token ···{token_id[-6:]}...",
                       {"token_suffix": token_id[-6:], "instrument_mode": "headless_s2s"})
            try:
                payment = db.query(Payment).filter(Payment.id == res["payment_id"]).first()
                headless_res = charge_headless(
                    db=db,
                    payment=payment,
                    razorpay_customer_id=rz_customer_id,
                    token_id=token_id,
                    user_email=current_user.email
                )
                yield emit("HEADLESS_CHARGE", "passed",
                           f"Payment captured — {headless_res['razorpay_payment_id']}",
                           {
                               "razorpay_payment_id": headless_res["razorpay_payment_id"],
                               "instrument_mode": "headless_s2s",
                               "receipt_url": headless_res.get("receipt_url")
                           })
                # Merge headless result into res for final_result event
                res.update(headless_res)
                yield json.dumps({"type": "final_result", "data": res}) + "\n"
                return

            except SavedInstrumentInvalid as e:
                yield emit("HEADLESS_CHARGE", "blocked",
                           "Saved payment method is invalid or expired. Please re-authorize in your Profile.",
                           {"error_class": "SavedInstrumentInvalid"})
                yield json.dumps({"type": "error", "error_class": "SavedInstrumentInvalid",
                                  "message": "Your saved payment method is invalid or expired. Go to Profile → Authorize Agent to Pay."}) + "\n"
                return

            except ChargeDeclined as e:
                yield emit("HEADLESS_CHARGE", "blocked",
                           f"Card issuer declined the charge: {e}",
                           {"error_class": "ChargeDeclined"})
                yield json.dumps({"type": "error", "error_class": "ChargeDeclined",
                                  "message": "The charge was declined by your card issuer. No retry was attempted automatically."}) + "\n"
                return

            except RazorpayProviderError as e:
                # S2S failed for provider reasons → fall through to Checkout.js fallback
                yield emit("HEADLESS_CHARGE", "blocked",
                           f"S2S charge unavailable ({e}) — falling back to checkout",
                           {"error_class": "RazorpayProviderError", "instrument_mode": "checkout_fallback_demo"})

        # STEP 5: Fallback — return order data for Checkout.js
        # This is the checkout_fallback path (no saved token, or S2S provider error)
        payment_mode = "checkout_fallback" if (token_id and rz_customer_id) else "checkout_no_token"
        yield emit("PAYMENT_READY", "passed",
                   f"Razorpay checkout ready — ₹{res.get('amount_rupees', res.get('amount', 0) / 100):,.2f}"
                   + (" [DEMO: no saved instrument, Checkout.js fallback]" if payment_mode == "checkout_no_token" else ""),
                   {"amount_rupees": res.get("amount_rupees"), "currency": "INR",
                    "payment_mode": payment_mode})

        res["payment_mode"] = payment_mode
        yield json.dumps({"type": "final_result", "data": res}) + "\n"

    except SpendingLimitNotConfigured as e:
        yield emit("LIMIT_CHECK", "blocked", str(e), {"error_class": "SpendingLimitNotConfigured"})
        yield json.dumps({"type": "error", "error_class": "SpendingLimitNotConfigured", "message": str(e)}) + "\n"

    except TransactionLimitExceeded as e:
        yield emit("LIMIT_CHECK", "blocked", str(e), {"error_class": "TransactionLimitExceeded"})
        yield json.dumps({"type": "error", "error_class": "TransactionLimitExceeded", "message": str(e)}) + "\n"

    except DailyLimitExceeded as e:
        yield emit("LIMIT_CHECK", "blocked", str(e), {"error_class": "DailyLimitExceeded"})
        yield json.dumps({"type": "error", "error_class": "DailyLimitExceeded", "message": str(e)}) + "\n"

    except InsufficientInventory as e:
        yield emit("ORDER_CREATING", "blocked", str(e), {"error_class": "InsufficientInventory"})
        yield json.dumps({"type": "error", "error_class": "InsufficientInventory", "message": str(e)}) + "\n"

    except RazorpayProviderError as e:
        yield emit("ORDER_CREATING", "blocked",
                   f"Payment provider error: {str(e)}", {"error_class": "RazorpayProviderError"})
        yield json.dumps({"type": "error", "error_class": "RazorpayProviderError",
                          "message": f"Razorpay provider error: {str(e)}"}) + "\n"

    except PaymentStateError as e:
        yield emit("ORDER_CREATING", "blocked", str(e), {"error_class": "PaymentStateError"})
        yield json.dumps({"type": "error", "error_class": "PaymentStateError", "message": str(e)}) + "\n"

    except Exception as e:
        import traceback
        traceback.print_exc()
        yield emit("ORDER_CREATING", "blocked",
                   "An unexpected error occurred.", {"error_class": type(e).__name__, "detail": str(e)})
        yield json.dumps({"type": "error", "error_class": "InternalError",
                          "message": "An internal error occurred during payment execution."}) + "\n"




@router.post("/execute-purchase")
def execute_purchase(
    request: ExecutePurchaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """
    Streams NDJSON step events as the agent executes a purchase.
    Each event has: {type, step, status, detail, metadata?}
    Final event has: {type: "final_result", data: {...}}
    Error event has: {type: "error", error_class, message}
    """
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    customer_id = str(customer.id)

    return StreamingResponse(
        _execute_purchase_stream(request, customer_id, db, current_user=current_user),
        media_type="application/x-ndjson"
    )


from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import logging
from typing import Optional

logger = logging.getLogger(__name__)

from app.db.session import get_db
from app.models.order import Order, Payment
from app.models.audit import AuditLog
from app.payment.service import create_payment_order, verify_payment, create_direct_payment_order
from app.payment.exceptions import PaymentStateError, PaymentVerificationError
from app.payment.schemas import RazorpayOrderRequest, RazorpayVerifyRequest, PaymentStatusResponse, DirectCheckoutRequest
from pydantic import BaseModel
from decimal import Decimal
from app.api.auth import get_current_customer_user, verify_customer_ownership, resolve_customer, get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/create-order")
def create_order(request: RazorpayOrderRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    if not request.human_approval:
        raise HTTPException(status_code=400, detail="Human approval is required to create a payment order.")
    try:
        res = create_payment_order(
            db, 
            request.merchant_id, 
            str(customer.id),
            request.cart_id,
            request.source,
            request.agent_trace,
            request.human_approval
        )
        return res
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in create_order")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post("/create-direct-order")
def create_direct_order(request: DirectCheckoutRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    customer = resolve_customer(db, current_user, request.merchant_id, request.customer_id)
    if not request.human_approval:
        raise HTTPException(status_code=400, detail="Human approval is required to create a direct payment order.")
    try:
        request.customer_id = str(customer.id)
        res = create_direct_payment_order(db, request)
        return res
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in create_direct_order")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

@router.post("/verify")
def verify_payment_route(request: RazorpayVerifyRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    from app.models.order import Payment
    payment = db.query(Payment).filter(Payment.id == request.payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    verify_customer_ownership(db, str(payment.order.customer_id), current_user)
    
    try:
        res = verify_payment(
            db, 
            request.payment_id, 
            request.razorpay_payment_id, 
            request.razorpay_order_id, 
            request.razorpay_signature
        )
        return res
    except PaymentVerificationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PaymentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in verify_payment_route")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

# Agentic token routes removed as requested

@router.get("/{payment_id}/status", response_model=PaymentStatusResponse)
def get_payment_status(payment_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    from app.models.order import Payment
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    verify_customer_ownership(db, str(payment.order.customer_id), current_user)
    return {"payment_id": payment.id, "status": payment.status}

# Agentic token routes removed as requested

from app.payment.schemas import PaymentHistoryResponse
from app.models.order import Payment

@router.get("/history", response_model=PaymentHistoryResponse)
def get_payment_history(db: Session = Depends(get_db), current_user: User = Depends(get_current_customer_user)):
    from app.models.customer import Customer
    customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
    if not customer:
        return PaymentHistoryResponse(payments=[])
        
    payments = db.query(Payment).join(Payment.order).filter(
        Payment.order.has(customer_id=customer.id)
    ).order_by(Payment.created_at.desc()).all()
    
    result = []
    for p in payments:
        result.append({
            "id": str(p.id),
            "local_order_id": str(p.order.order_number),
            "razorpay_order_id": p.provider_order_id,
            "razorpay_payment_id": p.provider_payment_id,
            "amount": float(p.amount),
            "currency": p.currency,
            "status": p.status,
            "webhook_verified": p.webhook_verified,
            "created_at": p.created_at.isoformat() if p.created_at else ""
        })
        
    return PaymentHistoryResponse(payments=result)

from typing import Any, List, Dict

@router.get("/audit", response_model=List[Dict[str, Any]])
def get_audit_logs(
    merchant_id: str,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """
    Get recent audit logs.
    """
    customer = resolve_customer(db, current_user, merchant_id)
    logs = db.query(AuditLog).filter(
        AuditLog.customer_id == customer.id,
        AuditLog.merchant_id == merchant_id
    ).order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": str(log.id),
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "action": log.action,
            "event_type": log.event_type,
            "actor_type": log.actor_type,
            "metadata": log.metadata_json
        } for log in logs
    ]

@router.get("/audit/{order_ref}", response_model=List[Dict[str, Any]])
def get_order_audit_logs(
    order_ref: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_customer_user)
):
    """
    Get audit logs for a specific order.
    order_ref can be either the UUID or the human-readable order_number (e.g. ORD-2026-ABCDEF).
    """
    from app.models.customer import Customer
    customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Resolve order_ref: try as UUID first, then as order_number string
    from app.models.order import Order
    import uuid as uuid_mod
    order = None
    try:
        order_uuid = uuid_mod.UUID(order_ref)
        order = db.query(Order).filter(
            Order.id == order_uuid,
            Order.customer_id == customer.id
        ).first()
    except (ValueError, AttributeError):
        pass

    if not order:
        # Try by order_number (human-readable string like ORD-2026-ABCDEF)
        order = db.query(Order).filter(
            Order.order_number == order_ref,
            Order.customer_id == customer.id
        ).first()

    if not order:
        return []

    logs = db.query(AuditLog).filter(
        AuditLog.customer_id == customer.id,
        AuditLog.order_id == order.id
    ).order_by(AuditLog.created_at.asc()).all()

    return [
        {
            "id": str(log.id),
            "created_at": log.created_at.isoformat() if log.created_at else None,
            "action": log.action,
            "event_type": log.event_type,
            "actor_type": log.actor_type,
            "metadata": log.metadata_json
        } for log in logs
    ]


# ─── Instrument Setup & Tokenization ──────────────────────────────────────────

class SetupInstrumentRequest(BaseModel):
    merchant_id: str

class SetupInstrumentResponse(BaseModel):
    razorpay_key_id: str
    razorpay_customer_id: str
    has_saved_token: bool
    token_suffix: str | None = None  # last 6 chars of token_id if already saved

@router.post("/setup-instrument", response_model=SetupInstrumentResponse)
def setup_instrument(
    req: SetupInstrumentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    One-time setup endpoint: ensures the user has a Razorpay customer record.
    Returns key_id and customer_id so the frontend can open Checkout.js in save mode.
    If a token is already saved, returns has_saved_token=True.
    """
    from app.payment.razorpay_client import get_or_create_customer, RAZORPAY_KEY_ID

    # Check if already set up
    if current_user.active_mandate_token and current_user.razorpay_customer_id:
        return {
            "razorpay_key_id": RAZORPAY_KEY_ID,
            "razorpay_customer_id": current_user.razorpay_customer_id,
            "has_saved_token": True,
            "token_suffix": current_user.active_mandate_token[-6:] if current_user.active_mandate_token else None
        }

    # Create Razorpay customer if we don't have one yet
    if not current_user.razorpay_customer_id:
        try:
            rz_cust_id = get_or_create_customer(
                name=current_user.full_name or current_user.email.split("@")[0],
                email=current_user.email
            )
            current_user.razorpay_customer_id = rz_cust_id
            db.commit()
        except Exception as e:
            logger.error(f"Failed to create Razorpay customer for {current_user.email}: {e}")
            raise HTTPException(status_code=502, detail=f"Could not create Razorpay customer: {e}")

    return {
        "razorpay_key_id": RAZORPAY_KEY_ID,
        "razorpay_customer_id": current_user.razorpay_customer_id,
        "has_saved_token": False,
        "token_suffix": None
    }


class SaveInstrumentTokenRequest(BaseModel):
    token_id: str
    razorpay_customer_id: str
    merchant_id: str

@router.post("/save-instrument-token")
def save_instrument_token(
    req: SaveInstrumentTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Saves the token_id returned by Razorpay Checkout (save=1 mode) onto the user record.
    This token is used for all future headless agent charges — no card entry needed.
    """
    from app.api.auth import resolve_customer

    # Validate ownership — customer_id must match the current user
    if req.razorpay_customer_id != current_user.razorpay_customer_id:
        # Allow saving a new customer_id (first setup)
        if current_user.razorpay_customer_id and current_user.razorpay_customer_id != req.razorpay_customer_id:
            raise HTTPException(status_code=403, detail="Razorpay customer ID mismatch")

    current_user.razorpay_customer_id = req.razorpay_customer_id
    current_user.active_mandate_token = req.token_id

    # Write audit log for transparency
    customer = resolve_customer(db, current_user, req.merchant_id)
    audit = AuditLog(
        merchant_id=req.merchant_id,
        customer_id=str(customer.id),
        action="INSTRUMENT_SAVED",
        event_type="authorization",
        actor_type="USER",
        metadata_json={
            "token_suffix": req.token_id[-6:],
            "razorpay_customer_id": req.razorpay_customer_id,
            "note": "User authorized agent to pay using saved instrument — one-time setup complete"
        }
    )
    db.add(audit)
    db.commit()

    return {
        "status": "saved",
        "token_suffix": req.token_id[-6:],
        "message": "Payment instrument saved. Your agent can now make payments without card entry."
    }


@router.delete("/instrument-token")
def revoke_instrument_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes the saved payment instrument (user can re-authorize at any time)."""
    current_user.active_mandate_token = None
    db.commit()
    return {"status": "revoked", "message": "Saved payment method removed. Add a new one in Profile."}


# ─── Receipt Generation ────────────────────────────────────────────────────────

@router.get("/receipt/{payment_id}", response_class=HTMLResponse)
def get_receipt(
    payment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Server-rendered HTML receipt for a captured payment.
    Pulls real data from Order, OrderItems, Payment, Merchant, Customer records.
    """
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    # Ownership check
    order = payment.order
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    from sqlalchemy import select
    from app.models.customer import Customer
    customer_rec = db.query(Customer).filter(Customer.id == order.customer_id).first()
    if not customer_rec or customer_rec.email != current_user.email:
        raise HTTPException(status_code=403, detail="Access denied")

    from app.models.merchant import Merchant
    merchant = db.query(Merchant).filter(Merchant.id == order.merchant_id).first()

    # Determine payment method label
    instrument_mode = "Razorpay Checkout"
    # Check audit logs for headless indicator
    headless_log = db.query(AuditLog).filter(
        AuditLog.order_id == order.id,
        AuditLog.action == "AGENT_CHARGED_SAVED_INSTRUMENT"
    ).first()
    if headless_log:
        instrument_mode = "Headless Agent Charge (Saved Instrument)"
        token_used = (headless_log.metadata_json or {}).get("token_id", "")
        if token_used:
            instrument_mode += f" ···{token_used[-6:]}"

    # Build items table rows
    items_html = ""
    for item in order.items:
        items_html += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0">{item.product_name}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:center">{item.quantity}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:right">₹{float(item.unit_price):,.2f}</td>
          <td style="padding:8px 12px;border-bottom:1px solid #f0f0f0;text-align:right">₹{float(item.subtotal):,.2f}</td>
        </tr>"""

    captured_at = payment.updated_at.strftime("%d %b %Y, %I:%M %p UTC") if payment.updated_at else "N/A"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Receipt — {order.order_number}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f7f8fa; color: #222; padding: 40px 20px; }}
    .receipt {{ max-width: 640px; margin: 0 auto; background: #fff; border-radius: 12px;
                box-shadow: 0 4px 24px rgba(0,0,0,0.10); overflow: hidden; }}
    .header {{ background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: white;
               padding: 32px 40px; }}
    .header h1 {{ font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
    .header .sub {{ font-size: 13px; opacity: 0.85; margin-top: 4px; }}
    .badge {{ display: inline-block; background: rgba(255,255,255,0.2); border-radius: 20px;
              padding: 4px 12px; font-size: 12px; margin-top: 8px; }}
    .body {{ padding: 32px 40px; }}
    .section {{ margin-bottom: 24px; }}
    .section-title {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px;
                      color: #888; margin-bottom: 10px; font-weight: 600; }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .field {{ background: #f7f8fa; border-radius: 8px; padding: 12px 14px; }}
    .field label {{ font-size: 11px; color: #888; display: block; margin-bottom: 3px; }}
    .field span {{ font-size: 14px; font-weight: 600; color: #222; word-break: break-all; }}
    table {{ width: 100%; border-collapse: collapse; }}
    thead th {{ background: #f7f8fa; padding: 8px 12px; font-size: 12px;
                text-align: left; color: #555; font-weight: 600; }}
    thead th:not(:first-child) {{ text-align: right; }}
    thead th:nth-child(2) {{ text-align: center; }}
    .total-row {{ font-size: 18px; font-weight: 700; color: #4f46e5; }}
    .footer {{ background: #f7f8fa; padding: 20px 40px; font-size: 12px; color: #aaa;
               text-align: center; border-top: 1px solid #eee; }}
    .pill {{ display: inline-block; background: #dcfce7; color: #166534; border-radius: 20px;
             padding: 4px 12px; font-size: 12px; font-weight: 600; }}
    @media print {{ body {{ padding: 0; }} .receipt {{ box-shadow: none; }} }}
  </style>
</head>
<body>
  <div class="receipt">
    <div class="header">
      <div class="sub">PAYMENT RECEIPT</div>
      <h1>{merchant.name if merchant else "Merchant"}</h1>
      <div class="badge">✓ Payment Captured</div>
    </div>
    <div class="body">

      <div class="section">
        <div class="section-title">Order Details</div>
        <div class="grid-2">
          <div class="field"><label>Order Number</label><span>{order.order_number}</span></div>
          <div class="field"><label>Status</label><span><span class="pill">PAID</span></span></div>
          <div class="field"><label>Date</label><span>{captured_at}</span></div>
          <div class="field"><label>Payment Method</label><span style="font-size:12px">{instrument_mode}</span></div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">Buyer</div>
        <div class="grid-2">
          <div class="field"><label>Name</label><span>{customer_rec.name}</span></div>
          <div class="field"><label>Email</label><span>{customer_rec.email or current_user.email}</span></div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">Items</div>
        <table>
          <thead><tr>
            <th>Item</th><th style="text-align:center">Qty</th>
            <th style="text-align:right">Unit Price</th><th style="text-align:right">Subtotal</th>
          </tr></thead>
          <tbody>{items_html}</tbody>
          <tfoot>
            <tr class="total-row">
              <td colspan="3" style="padding:16px 12px;text-align:right;font-size:14px;color:#555">Total</td>
              <td style="padding:16px 12px;text-align:right">₹{float(order.total):,.2f}</td>
            </tr>
          </tfoot>
        </table>
      </div>

      <div class="section">
        <div class="section-title">Razorpay Reference</div>
        <div class="grid-2">
          <div class="field"><label>Razorpay Order ID</label><span>{payment.provider_order_id or "—"}</span></div>
          <div class="field"><label>Razorpay Payment ID</label><span>{payment.provider_payment_id or "—"}</span></div>
          <div class="field"><label>Internal Payment ID</label><span>{str(payment.id)[:16]}…</span></div>
          <div class="field"><label>Currency</label><span>{payment.currency}</span></div>
        </div>
      </div>

    </div>
    <div class="footer">
      This receipt is auto-generated by the Agentic Commerce platform.<br>
      Powered by Razorpay • {captured_at}
      <br><br>
      <a href="javascript:window.print()" style="color:#4f46e5;text-decoration:none;font-weight:600">🖨 Print Receipt</a>
    </div>
  </div>
</body>
</html>"""

    return HTMLResponse(content=html)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID

from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.audit import AuditLog
from app.api.auth import get_current_merchant_user
from app.models.merchant import Merchant

router = APIRouter()

@router.get("")
def list_orders(db: Session = Depends(get_db), merchant: Merchant = Depends(get_current_merchant_user)):
    orders = db.scalars(
        select(Order)
        .filter(Order.merchant_id == merchant.id)
        .order_by(Order.created_at.desc())
    ).all()
    
    return [
        {
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status,
            "total": o.total,
            "created_at": o.created_at.isoformat(),
            "customer_name": o.customer.name,
            "items_count": len(o.items)
        } for o in orders
    ]

@router.get("/{order_id}")
def get_order(order_id: UUID, db: Session = Depends(get_db), merchant: Merchant = Depends(get_current_merchant_user)):
    
    order = db.scalar(
        select(Order)
        .filter(Order.id == order_id, Order.merchant_id == merchant.id)
    )
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    items = []
    for item in order.items:
        items.append({
            "id": item.id,
            "product_name": item.product_name,
            "sku": item.sku,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "subtotal": item.subtotal
        })
        
    # Get transaction trace from audit logs
    audit_logs = db.scalars(
        select(AuditLog)
        .filter(
            AuditLog.customer_id == order.customer_id, 
            AuditLog.merchant_id == merchant.id
        )
        .order_by(AuditLog.created_at.asc())
    ).all()
    
    # Filter logs that happened recently around the order
    trace = []
    for log in audit_logs:
        # Just return all logs for this customer as the trace for the demo
        trace.append({
            "id": log.id,
            "event_type": log.event_type,
            "action": log.action,
            "actor_type": log.actor_type,
            "created_at": log.created_at.isoformat(),
            "metadata": log.metadata_json
        })
        
    return {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "source": order.source,
        "subtotal": order.subtotal,
        "discount": order.discount,
        "total": order.total,
        "metadata_json": order.metadata_json,
        "created_at": order.created_at.isoformat(),
        "customer": {
            "name": order.customer.name,
            "email": order.customer.email
        },
        "items": items,
        "trace": trace
    }

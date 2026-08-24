from sqlalchemy.orm import Session
from sqlalchemy import select
from app.tools.base import CommerceTool, ToolError
from app.tools.schemas import GetCustomerContextInput
from app.models.customer import Customer, CustomerEvent

class GetCustomerContextTool(CommerceTool):
    name = "get_customer_context"
    description = "Retrieve commerce-relevant context for a specific customer."
    input_schema = GetCustomerContextInput
    read_only = True

    def execute(self, db_session: Session, **kwargs):
        merchant_id = kwargs.get("merchant_id")
        customer_id = kwargs.get("customer_id")

        customer = db_session.scalar(
            select(Customer).filter(Customer.id == customer_id, Customer.merchant_id == merchant_id)
        )

        if not customer:
            raise ToolError("CUSTOMER_NOT_FOUND", "The requested customer does not exist for this merchant.")

        recent_events = db_session.scalars(
            select(CustomerEvent)
            .filter(CustomerEvent.customer_id == customer_id)
            .order_by(CustomerEvent.created_at.desc())
            .limit(10)
        ).all()

        event_types = []
        recent_products = []
        for e in recent_events:
            event_types.append(e.event_type)
            if e.product and e.product.sku not in recent_products:
                recent_products.append(e.product.sku)

        return {
            "customer_id": str(customer.id),
            "name": customer.name,
            "budget_preference": float(customer.budget_preference) if customer.budget_preference and customer.budget_preference.replace('.', '', 1).isdigit() else None,
            "recent_products": recent_products[:5],
            "recent_events": list(set(event_types))
        }

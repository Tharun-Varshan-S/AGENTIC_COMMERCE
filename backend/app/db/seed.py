import uuid
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.merchant import Merchant, MerchantRule
from app.models.product import Product, Inventory
from app.models.customer import Customer, CustomerEvent
from app.models.order import Cart, CartItem, Order, Payment
from app.models.agent import AgentDecision
from app.models.audit import AuditLog

def seed_db():
    db: Session = SessionLocal()
    try:
        # Check if already seeded to prevent duplicates
        existing_merchant = db.scalars(select(Merchant).filter(Merchant.email == "hello@technovagaming.com")).first()
        if existing_merchant:
            print("Database already seeded. Skipping...")
            return

        print("Starting database seed...")

        # 1. Merchant
        merchant = Merchant(
            name="TechNova Gaming Store",
            description="Premium gaming peripherals and hardware.",
            email="hello@technovagaming.com",
            currency="INR",
            is_active=True
        )
        db.add(merchant)
        db.flush()

        # 2. Merchant Rules
        rule = MerchantRule(
            merchant_id=merchant.id,
            max_transaction_amount=Decimal('5000.00'),
            max_discount_percent=Decimal('15.00'),
            min_margin_percent=Decimal('10.00'),
            auto_approval_limit=Decimal('3000.00'),
            require_consent=True
        )
        db.add(rule)

        # 3. Products
        products_data = [
            {"sku": "G304", "name": "G304 Gaming Mouse", "category": "Gaming", "price": Decimal('1999.00'), "stock": 50},
            {"sku": "G502", "name": "G502 Gaming Mouse", "category": "Gaming", "price": Decimal('3499.00'), "stock": 25},
            {"sku": "MP01", "name": "MP01 Gaming Mousepad", "category": "Accessories", "price": Decimal('799.00'), "stock": 100},
            {"sku": "K01", "name": "K01 Mechanical Gaming Keyboard", "category": "Gaming", "price": Decimal('2499.00'), "stock": 30},
            {"sku": "H01", "name": "H01 Gaming Headset", "category": "Audio", "price": Decimal('2199.00'), "stock": 15},
            {"sku": "WEBCAM01", "name": "1080p Gaming Webcam", "category": "Streaming", "price": Decimal('2799.00'), "stock": 2} # Low stock
        ]
        
        products = []
        for pdata in products_data:
            prod = Product(
                merchant_id=merchant.id,
                sku=pdata["sku"],
                name=pdata["name"],
                category=pdata["category"],
                price=pdata["price"],
                currency="INR",
                is_active=True
            )
            db.add(prod)
            db.flush()
            products.append(prod)
            
            # Inventory
            inv = Inventory(
                product_id=prod.id,
                quantity=pdata["stock"],
                reserved_quantity=0,
                reorder_level=10
            )
            db.add(inv)

        # 4. Customers
        customers_data = [
            {"name": "Arun", "email": "arun@demo.com"},
            {"name": "Priya", "email": "priya@demo.com"},
            {"name": "Rahul", "email": "rahul@demo.com"},
            {"name": "Kavin", "email": "kavin@demo.com"},
            {"name": "Ananya", "email": "ananya@demo.com"}
        ]
        
        customers = []
        for cdata in customers_data:
            cust = Customer(
                merchant_id=merchant.id,
                name=cdata["name"],
                email=cdata["email"]
            )
            db.add(cust)
            db.flush()
            customers.append(cust)

        # 5. Customer Events
        arun = customers[0]
        events = [
            CustomerEvent(customer_id=arun.id, event_type="product_view", product_id=products[0].id),
            CustomerEvent(customer_id=arun.id, event_type="product_view", product_id=products[2].id),
            CustomerEvent(customer_id=arun.id, event_type="add_to_cart", product_id=products[0].id)
        ]
        db.add_all(events)
        db.flush()

        # 6. Carts and Orders
        cart = Cart(
            customer_id=arun.id,
            merchant_id=merchant.id,
            status="CHECKOUT",
            currency="INR"
        )
        db.add(cart)
        db.flush()

        cart_item = CartItem(
            cart_id=cart.id,
            product_id=products[0].id,
            quantity=1,
            unit_price=products[0].price
        )
        db.add(cart_item)
        db.flush()

        order = Order(
            merchant_id=merchant.id,
            customer_id=arun.id,
            cart_id=cart.id,
            order_number="ORD-2026-000001",
            status="PENDING",
            currency="INR",
            subtotal=products[0].price,
            discount=Decimal('0.00'),
            total=products[0].price
        )
        db.add(order)
        db.flush()

        # 7. Agent Decisions (Demo)
        decision = AgentDecision(
            customer_id=arun.id,
            merchant_id=merchant.id,
            session_id=str(uuid.uuid4()),
            intent="purchase_mouse",
            primary_product_id=products[0].id,
            intervention_type="CROSS_SELL",
            recommended_product_id=products[2].id,
            reason="Customer looking at mouse, suggest mousepad",
            expected_order_value=products[0].price + products[2].price
        )
        db.add(decision)

        # 8. Audit Logs
        audit = AuditLog(
            merchant_id=merchant.id,
            customer_id=arun.id,
            order_id=order.id,
            event_type="ORDER_CREATED",
            actor_type="CUSTOMER",
            action="Placed an order"
        )
        db.add(audit)

        db.commit()
        print("Database seeded successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()

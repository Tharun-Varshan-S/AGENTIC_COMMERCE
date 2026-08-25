import uuid
import random
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text

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
        print("Cleaning up database...")
        db.execute(text("TRUNCATE TABLE merchants CASCADE;"))
        db.commit()

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
                cost_price=pdata["price"] * Decimal('0.60'), # 40% margin
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

        # Generate historical orders for last 7 days
        now = datetime.now()
        
        for i in range(7):
            date_shift = now - timedelta(days=i)
            # 2 to 5 orders per day
            num_orders = random.randint(2, 5)
            for j in range(num_orders):
                cust = random.choice(customers)
                is_ai = random.choice([True, False])
                prod1 = random.choice(products)
                prod2 = random.choice(products) if random.random() > 0.7 else None
                
                # Cart
                cart = Cart(
                    customer_id=cust.id,
                    merchant_id=merchant.id,
                    status="COMPLETED",
                    currency="INR",
                    created_at=date_shift,
                    updated_at=date_shift
                )
                db.add(cart)
                db.flush()

                # Items
                total = prod1.price
                items = [CartItem(cart_id=cart.id, product_id=prod1.id, quantity=1, unit_price=prod1.price, created_at=date_shift)]
                if prod2:
                    total += prod2.price
                    items.append(CartItem(cart_id=cart.id, product_id=prod2.id, quantity=1, unit_price=prod2.price, created_at=date_shift))
                db.add_all(items)

                # Order
                order_num = f"ORD-{date_shift.strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
                order = Order(
                    merchant_id=merchant.id,
                    customer_id=cust.id,
                    cart_id=cart.id,
                    order_number=order_num,
                    status="PAID",
                    source="AI" if is_ai else "DIRECT",
                    currency="INR",
                    subtotal=total,
                    discount=Decimal('0.00'),
                    total=total,
                    created_at=date_shift,
                    updated_at=date_shift
                )
                db.add(order)
                db.flush()

                # Agent Decision (if AI)
                if is_ai and prod2:
                    decision = AgentDecision(
                        customer_id=cust.id,
                        merchant_id=merchant.id,
                        session_id=str(uuid.uuid4()),
                        intent=f"purchase_{prod1.category.lower()}",
                        primary_product_id=prod1.id,
                        intervention_type="CROSS_SELL",
                        recommended_product_id=prod2.id,
                        reason=f"Customer looking at {prod1.name}, suggest {prod2.name}",
                        expected_order_value=total,
                        created_at=date_shift,
                        updated_at=date_shift
                    )
                    db.add(decision)

        # Generate 4 high-fidelity demo scenarios for the Activity Feed (A, B, C, D)
        print("Generating specific demo scenarios...")
        demo_cust = customers[0]
        
        # Scenario A: Cross-sell Accepted (Full Funnel)
        decision_a = AgentDecision(
            customer_id=demo_cust.id, merchant_id=merchant.id, session_id=str(uuid.uuid4()),
            intent="purchase_gaming_mouse", primary_product_id=products[0].id, intervention_type="CROSS_SELL",
            recommended_product_id=products[2].id, reason="Pairs well with G304", score=0.92,
            expected_order_value=products[0].price + products[2].price, created_at=now
        )
        db.add(decision_a)
        
        logs_a = [
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action="Received intent: purchase_gaming_mouse", event_type="INTENT_RECEIVED", actor_type="SYSTEM", created_at=now - timedelta(minutes=10)),
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action=f"Discovered {products[0].name}", event_type="PRODUCT_DISCOVERED", actor_type="SYSTEM", created_at=now - timedelta(minutes=9)),
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action=f"Recommended {products[2].name}", event_type="RECOMMENDATION_MADE", actor_type="AGENT", created_at=now - timedelta(minutes=8)),
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action=f"Accepted {products[2].name}", event_type="RECOMMENDATION_ACCEPTED", actor_type="USER", created_at=now - timedelta(minutes=7)),
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action="Started checkout", event_type="CHECKOUT_STARTED", actor_type="USER", created_at=now - timedelta(minutes=6)),
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action="Payment successful", event_type="PAYMENT_CAPTURED", actor_type="SYSTEM", created_at=now - timedelta(minutes=5))
        ]
        db.add_all(logs_a)
        
        # Scenario B: Policy Engine Rejection (Too high transaction amount)
        logs_b = [
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action="Attempted bulk checkout", event_type="CHECKOUT_STARTED", actor_type="USER", created_at=now - timedelta(minutes=30)),
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action="Policy rejected: Exceeds max transaction limit", event_type="POLICY_EVALUATED", actor_type="POLICY_ENGINE", metadata_json={"decision": "REJECTED", "reason": "MAX_AMOUNT_EXCEEDED"}, created_at=now - timedelta(minutes=29))
        ]
        db.add_all(logs_b)
        
        # Scenario C: Consent Flow
        logs_c = [
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action="Checkout flagged for consent", event_type="POLICY_EVALUATED", actor_type="POLICY_ENGINE", metadata_json={"decision": "REQUIRES_CONSENT", "reason": "HIGH_VALUE_B2B"}, created_at=now - timedelta(minutes=60)),
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action="Consent request sent to merchant", event_type="CONSENT_REQUESTED", actor_type="SYSTEM", created_at=now - timedelta(minutes=59)),
            AuditLog(merchant_id=merchant.id, customer_id=demo_cust.id, action="Merchant approved transaction", event_type="CONSENT_APPROVED", actor_type="MERCHANT", created_at=now - timedelta(minutes=45))
        ]
        db.add_all(logs_c)

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

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

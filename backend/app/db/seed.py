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
from app.models.promotion import Promotion
from app.models.user import User
from app.core.security import get_password_hash

def seed_db():
    db: Session = SessionLocal()
    try:
        print("Cleaning up database...")
        db.execute(text("TRUNCATE TABLE merchants, users CASCADE;"))
        db.commit()

        print("Starting database seed...")

        # 1. Merchants
        merchant_tn = Merchant(
            name="TechNova Gaming Store",
            description="Premium gaming peripherals and hardware.",
            email="hello@technovagaming.com",
            currency="INR",
            is_active=True
        )
        merchant_az = Merchant(
            name="Amazon (Demo)",
            description="Amazon demo source.",
            email="amazon@demo.com",
            currency="INR",
            is_active=True
        )
        merchant_fk = Merchant(
            name="Flipkart (Demo)",
            description="Flipkart demo source.",
            email="flipkart@demo.com",
            currency="INR",
            is_active=True
        )
        db.add_all([merchant_tn, merchant_az, merchant_fk])
        db.flush()

        # 1.5 Users
        demo_password = get_password_hash("password123")
        
        user_tn = User(
            email="merchant@demo.local",
            hashed_password=demo_password,
            full_name="TechNova Admin",
            role="MERCHANT_ADMIN",
            merchant_id=merchant_tn.id
        )
        user_az = User(
            email="amazon@demo.local",
            hashed_password=demo_password,
            full_name="Amazon Demo Admin",
            role="MERCHANT_ADMIN",
            merchant_id=merchant_az.id
        )
        user_fk = User(
            email="flipkart@demo.local",
            hashed_password=demo_password,
            full_name="Flipkart Demo Admin",
            role="MERCHANT_ADMIN",
            merchant_id=merchant_fk.id
        )
        user_cust = User(
            email="customer@demo.local",
            hashed_password=demo_password,
            full_name="Demo Customer",
            role="CUSTOMER"
        )
        db.add_all([user_tn, user_az, user_fk, user_cust])
        db.flush()
        print("Created demo users with password 'password123'")


        # 2. Merchant Rules (Only for TechNova)
        rule = MerchantRule(
            merchant_id=merchant_tn.id,
            max_transaction_amount=Decimal('50000.00'),
            max_discount_percent=Decimal('15.00'),
            min_margin_percent=Decimal('10.00'),
            auto_approval_limit=Decimal('30000.00'),
            require_consent=True
        )
        db.add(rule)

        # 3. Products
        products_data = [
            # Razorpay Merchant Products
            {"sku": "G304", "name": "G304 Gaming Mouse", "category": "Gaming", "price": Decimal('1999.00'), "mrp": Decimal('2495.00'), "stock": 50, "source": "razorpay", "merchant_id": merchant_tn.id, "rating": Decimal('4.6'), "review_count": 342, "is_sponsored": True, "delivery_estimate": "Tomorrow", "image_url": "https://images.unsplash.com/photo-1527814050087-3793815479db?w=600&q=80"},
            {"sku": "G502", "name": "G502 Gaming Mouse", "category": "Gaming", "price": Decimal('3499.00'), "mrp": Decimal('4999.00'), "stock": 25, "source": "razorpay", "merchant_id": merchant_tn.id, "rating": Decimal('4.8'), "review_count": 512, "is_sponsored": False, "delivery_estimate": "Tomorrow", "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&q=80"},
            {"sku": "K01", "name": "K01 Mechanical Gaming Keyboard", "category": "Gaming", "price": Decimal('2499.00'), "mrp": Decimal('3999.00'), "stock": 30, "source": "razorpay", "merchant_id": merchant_tn.id, "rating": Decimal('4.5'), "review_count": 128, "is_sponsored": False, "delivery_estimate": "2 Days", "image_url": "https://images.unsplash.com/photo-1595225476474-87563907a212?w=600&q=80"},
            
            # Smartphones
            {"sku": "AMZ-PH1", "name": "Samsung Galaxy S24", "category": "Smartphone", "price": Decimal('74999.00'), "mrp": Decimal('79999.00'), "stock": 100, "source": "amazon", "merchant_id": merchant_az.id, "rating": Decimal('4.7'), "review_count": 1024, "is_sponsored": False, "delivery_estimate": "Tomorrow", "image_url": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=600&q=80"},
            {"sku": "AMZ-PH2", "name": "OnePlus 12R", "category": "Smartphone", "price": Decimal('39999.00'), "mrp": Decimal('42999.00'), "stock": 40, "source": "amazon", "merchant_id": merchant_az.id, "rating": Decimal('4.5'), "review_count": 890, "is_sponsored": False, "delivery_estimate": "Tomorrow", "image_url": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&q=80"},
            {"sku": "FLK-PH1", "name": "Google Pixel 8a", "category": "Smartphone", "price": Decimal('44999.00'), "mrp": Decimal('52999.00'), "stock": 30, "source": "flipkart", "merchant_id": merchant_fk.id, "rating": Decimal('4.4'), "review_count": 500, "is_sponsored": False, "delivery_estimate": "3 Days", "image_url": "https://images.unsplash.com/photo-1596742578443-7682ef5251cd?w=600&q=80"},
            {"sku": "RZP-PH1", "name": "Nothing Phone (2a)", "category": "Smartphone", "price": Decimal('25999.00'), "mrp": Decimal('29999.00'), "stock": 50, "source": "razorpay", "merchant_id": merchant_tn.id, "rating": Decimal('4.3'), "review_count": 320, "is_sponsored": True, "delivery_estimate": "Tomorrow", "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&q=80"},
            
            # Audio / Headphones
            {"sku": "AMZ-HD1", "name": "Sony WH-1000XM5", "category": "Audio", "price": Decimal('26990.00'), "mrp": Decimal('34990.00'), "stock": 80, "source": "amazon", "merchant_id": merchant_az.id, "rating": Decimal('4.8'), "review_count": 2100, "is_sponsored": False, "delivery_estimate": "2 Days", "image_url": "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=600&q=80"},
            {"sku": "FLK-HD1", "name": "Boat Rockerz 450", "category": "Audio", "price": Decimal('1499.00'), "mrp": Decimal('3990.00'), "stock": 200, "source": "flipkart", "merchant_id": merchant_fk.id, "rating": Decimal('4.1'), "review_count": 5600, "is_sponsored": False, "delivery_estimate": "Tomorrow", "image_url": "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=600&q=80"},
            {"sku": "RZP-HD1", "name": "Noise Wireless Pro", "category": "Audio", "price": Decimal('1999.00'), "mrp": Decimal('2999.00'), "stock": 150, "source": "razorpay", "merchant_id": merchant_tn.id, "rating": Decimal('4.2'), "review_count": 450, "is_sponsored": True, "delivery_estimate": "Tomorrow", "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80"}
        ]
        
        products = []
        sponsored_products = []
        for pdata in products_data:
            prod = Product(
                merchant_id=pdata["merchant_id"],
                sku=pdata["sku"],
                name=pdata["name"],
                category=pdata["category"],
                price=pdata["price"],
                mrp=pdata["mrp"],
                image_url=pdata["image_url"],
                cost_price=pdata["price"] * Decimal('0.60'), # 40% margin
                currency="INR",
                is_active=True,
                source=pdata["source"],
                rating=pdata["rating"],
                review_count=pdata["review_count"],
                is_sponsored=pdata["is_sponsored"],
                delivery_estimate=pdata["delivery_estimate"]
            )
            db.add(prod)
            db.flush()
            products.append(prod)
            
            if pdata["is_sponsored"]:
                sponsored_products.append(prod)
            
            # Inventory
            inv = Inventory(
                product_id=prod.id,
                quantity=pdata["stock"],
                reserved_quantity=0,
                reorder_level=10
            )
            db.add(inv)
            
        # Add Promotions for sponsored products
        now = datetime.now()
        for sprod in sponsored_products:
            promo = Promotion(
                merchant_id=merchant_tn.id,
                product_id=sprod.id,
                budget=Decimal('5000.00'),
                remaining_budget=Decimal('4250.00'),
                priority=10,
                status="ACTIVE",
                target_category=sprod.category,
                impressions=random.randint(500, 2000),
                agent_recommendations=random.randint(50, 200),
                clicks=random.randint(20, 100),
                conversions=random.randint(5, 20),
                start_date=now - timedelta(days=5),
                end_date=now + timedelta(days=25)
            )
            db.add(promo)

        # 4. Customers
        customers_data = [
            {"name": "Arun", "email": "arun@demo.com"},
            {"name": "Priya", "email": "priya@demo.com"},
            {"name": "Rahul", "email": "rahul@demo.com"}
        ]
        
        customers = []
        for cdata in customers_data:
            cust = Customer(
                merchant_id=merchant_tn.id,
                name=cdata["name"],
                email=cdata["email"]
            )
            db.add(cust)
            db.flush()
            customers.append(cust)

        # Generate historical orders for last 7 days
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
                    merchant_id=merchant_tn.id,
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
                    merchant_id=merchant_tn.id,
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
                        merchant_id=merchant_tn.id,
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

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
from app.models.offer import Offer
from app.core.security import get_password_hash

def seed_db():
    db: Session = SessionLocal()
    try:
        print("Cleaning up database...")
        db.execute(text("TRUNCATE TABLE merchants, users, products, offers CASCADE;"))
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

        # 3. Products and Offers
        products_data = [
            {"sku": "G304", "name": "G304 Gaming Mouse", "category": "Gaming", "image_url": "https://images.unsplash.com/photo-1527814050087-3793815479db?w=600&q=80", "offers": [
                {"merchant_id": merchant_tn.id, "price": Decimal('1999.00'), "mrp": Decimal('2495.00'), "stock": 50, "source": "razorpay", "is_sponsored": True, "delivery": "Tomorrow"},
                {"merchant_id": merchant_az.id, "price": Decimal('2099.00'), "mrp": Decimal('2495.00'), "stock": 10, "source": "amazon", "is_sponsored": False, "delivery": "3 Days"}
            ]},
            {"sku": "G502", "name": "G502 Gaming Mouse", "category": "Gaming", "image_url": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=600&q=80", "offers": [
                {"merchant_id": merchant_tn.id, "price": Decimal('3499.00'), "mrp": Decimal('4999.00'), "stock": 25, "source": "razorpay", "is_sponsored": False, "delivery": "Tomorrow"}
            ]},
            {"sku": "K01", "name": "K01 Mechanical Gaming Keyboard", "category": "Gaming", "image_url": "https://images.unsplash.com/photo-1595225476474-87563907a212?w=600&q=80", "offers": [
                {"merchant_id": merchant_tn.id, "price": Decimal('2499.00'), "mrp": Decimal('3999.00'), "stock": 30, "source": "razorpay", "is_sponsored": False, "delivery": "2 Days"}
            ]},
            
            # Smartphones
            {"sku": "PH1-S24", "name": "Samsung Galaxy S24", "category": "Smartphone", "image_url": "https://images.unsplash.com/photo-1610945265064-0e34e5519bbf?w=600&q=80", "offers": [
                {"merchant_id": merchant_az.id, "price": Decimal('74999.00'), "mrp": Decimal('79999.00'), "stock": 100, "source": "amazon", "is_sponsored": False, "delivery": "Tomorrow"},
                {"merchant_id": merchant_fk.id, "price": Decimal('75999.00'), "mrp": Decimal('79999.00'), "stock": 45, "source": "flipkart", "is_sponsored": False, "delivery": "2 Days"}
            ]},
            {"sku": "PH2-12R", "name": "OnePlus 12R", "category": "Smartphone", "image_url": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=600&q=80", "offers": [
                {"merchant_id": merchant_az.id, "price": Decimal('39999.00'), "mrp": Decimal('42999.00'), "stock": 40, "source": "amazon", "is_sponsored": False, "delivery": "Tomorrow"}
            ]},
            {"sku": "PH3-P8A", "name": "Google Pixel 8a", "category": "Smartphone", "image_url": "https://images.unsplash.com/photo-1596742578443-7682ef5251cd?w=600&q=80", "offers": [
                {"merchant_id": merchant_fk.id, "price": Decimal('44999.00'), "mrp": Decimal('52999.00'), "stock": 30, "source": "flipkart", "is_sponsored": False, "delivery": "3 Days"}
            ]},
            {"sku": "PH4-N2A", "name": "Nothing Phone (2a)", "category": "Smartphone", "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600&q=80", "offers": [
                {"merchant_id": merchant_tn.id, "price": Decimal('25999.00'), "mrp": Decimal('29999.00'), "stock": 50, "source": "razorpay", "is_sponsored": True, "delivery": "Tomorrow"}
            ]},
            
            # Audio / Headphones
            {"sku": "HD1-XM5", "name": "Sony WH-1000XM5", "category": "Audio", "image_url": "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=600&q=80", "offers": [
                {"merchant_id": merchant_az.id, "price": Decimal('26990.00'), "mrp": Decimal('34990.00'), "stock": 80, "source": "amazon", "is_sponsored": False, "delivery": "2 Days"}
            ]},
            {"sku": "HD2-R450", "name": "Boat Rockerz 450", "category": "Audio", "image_url": "https://images.unsplash.com/photo-1583394838336-acd977736f90?w=600&q=80", "offers": [
                {"merchant_id": merchant_fk.id, "price": Decimal('1499.00'), "mrp": Decimal('3990.00'), "stock": 200, "source": "flipkart", "is_sponsored": False, "delivery": "Tomorrow"}
            ]},
            {"sku": "HD3-NWP", "name": "Noise Wireless Pro", "category": "Audio", "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600&q=80", "offers": [
                {"merchant_id": merchant_tn.id, "price": Decimal('1999.00'), "mrp": Decimal('2999.00'), "stock": 150, "source": "razorpay", "is_sponsored": True, "delivery": "Tomorrow"}
            ]}
        ]
        
        offers_list = []
        sponsored_products = []
        for pdata in products_data:
            # Create the global product
            prod = Product(
                sku=pdata["sku"],
                name=pdata["name"],
                category=pdata["category"],
                image_url=pdata["image_url"],
                rating=Decimal('4.5'), # Mock rating for global product
                review_count=random.randint(100, 2000)
            )
            db.add(prod)
            db.flush()
            
            # Create offers for this product
            for odata in pdata["offers"]:
                offer = Offer(
                    product_id=prod.id,
                    merchant_id=odata["merchant_id"],
                    price=odata["price"],
                    mrp=odata["mrp"],
                    currency="INR",
                    delivery_estimate=odata["delivery"],
                    is_active=True,
                    is_sponsored=odata["is_sponsored"],
                    source=odata["source"]
                )
                db.add(offer)
                db.flush()
                offers_list.append(offer)
                
                if odata["is_sponsored"]:
                    sponsored_products.append(prod)
                
                # Inventory belongs to the offer
                inv = Inventory(
                    offer_id=offer.id,
                    quantity=odata["stock"],
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
                offer1 = random.choice(offers_list)
                offer2 = random.choice(offers_list) if random.random() > 0.7 else None
                
                # Cart
                cart = Cart(
                    customer_id=cust.id,
                    merchant_id=offer1.merchant_id,
                    status="COMPLETED",
                    currency="INR",
                    created_at=date_shift,
                    updated_at=date_shift
                )
                db.add(cart)
                db.flush()

                # Items
                total = offer1.price
                items = [CartItem(cart_id=cart.id, offer_id=offer1.id, quantity=1, unit_price=offer1.price, created_at=date_shift)]
                if offer2:
                    total += offer2.price
                    items.append(CartItem(cart_id=cart.id, offer_id=offer2.id, quantity=1, unit_price=offer2.price, created_at=date_shift))
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
                if is_ai and offer2:
                    decision = AgentDecision(
                        customer_id=cust.id,
                        merchant_id=offer1.merchant_id,
                        session_id=str(uuid.uuid4()),
                        intent=f"purchase_{offer1.product.category.lower()}",
                        primary_product_id=offer1.product_id,
                        intervention_type="CROSS_SELL",
                        recommended_product_id=offer2.product_id,
                        reason=f"Customer looking at {offer1.product.name}, suggest {offer2.product.name}",
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

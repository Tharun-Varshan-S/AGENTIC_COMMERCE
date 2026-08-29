import pytest
from decimal import Decimal
import uuid
from app.revenue import RevenueEngine, RevenueRecommendationRequest
from app.models.merchant import Merchant
from app.models.product import Product, Inventory
from app.models.offer import Offer
from app.models.customer import Customer, CustomerEvent
from app.db.session import SessionLocal
import app.db.base # Ensure all models are loaded for SQLAlchemy registry

@pytest.fixture(scope="function")
def db_session():
    session = SessionLocal()
    yield session
    # In tests we should ideally rollback or use a clean DB, but for now we rollback to not commit dummy data
    session.rollback()
    session.close()

def test_recommend_cross_sell(db_session):
    # Setup test data
    merchant = Merchant(name="Test Merchant", email="test@merchant.com", is_active=True, currency="INR")
    db_session.add(merchant)
    db_session.flush()

    customer = Customer(merchant_id=merchant.id, name="Test Customer", email="test@test.com")
    db_session.add(customer)
    db_session.flush()

    # Primary Product: Gaming Mouse
    sku1 = f"M1-{uuid.uuid4().hex[:8]}"
    primary = Product(merchant_id=merchant.id, sku=sku1, name="Gaming Mouse", category="Gaming")
    db_session.add(primary)
    db_session.flush()
    offer1 = Offer(product_id=primary.id, merchant_id=merchant.id, price=Decimal("100.00"), mrp=Decimal("100.00"))
    db_session.add(offer1)
    db_session.flush()
    db_session.add(Inventory(offer_id=offer1.id, quantity=10, reorder_level=0))

    # Candidate 1: Mousepad (Accessories) - Should be Cross-Sell
    sku2 = f"MP1-{uuid.uuid4().hex[:8]}"
    candidate_cs = Product(merchant_id=merchant.id, sku=sku2, name="Mousepad", category="Accessories")
    db_session.add(candidate_cs)
    db_session.flush()
    offer2 = Offer(product_id=candidate_cs.id, merchant_id=merchant.id, price=Decimal("20.00"), mrp=Decimal("20.00"))
    db_session.add(offer2)
    db_session.flush()
    db_session.add(Inventory(offer_id=offer2.id, quantity=50, reorder_level=0))
    db_session.commit()

    engine = RevenueEngine(db_session)
    request = RevenueRecommendationRequest(
        merchant_id=merchant.id,
        customer_id=customer.id,
        primary_product_id=primary.id,
        customer_intent="buy gaming mouse",
        customer_budget=Decimal("200.00")
    )
    
    response = engine.recommend(request)
    assert response.intervention == "CROSS_SELL"
    assert response.recommended_product.id == candidate_cs.id
    assert response.score >= 0.55
    assert len(response.factors) > 0

def test_recommend_upsell(db_session):
    merchant = Merchant(name="Test Merchant", email="test@merchant.com", is_active=True, currency="INR")
    db_session.add(merchant)
    db_session.flush()

    customer = Customer(merchant_id=merchant.id, name="Test Customer", email="test@test.com")
    db_session.add(customer)
    db_session.flush()

    sku1 = f"M1-{uuid.uuid4().hex[:8]}"
    primary = Product(merchant_id=merchant.id, sku=sku1, name="Gaming Mouse", category="Gaming")
    db_session.add(primary)
    db_session.flush()
    offer1 = Offer(product_id=primary.id, merchant_id=merchant.id, price=Decimal("100.00"), mrp=Decimal("100.00"))
    db_session.add(offer1)
    db_session.flush()
    db_session.add(Inventory(offer_id=offer1.id, quantity=10, reorder_level=0))

    # Candidate: Better Mouse (Gaming) - Should be Upsell
    sku2 = f"M2-{uuid.uuid4().hex[:8]}"
    candidate_us = Product(merchant_id=merchant.id, sku=sku2, name="Pro Gaming Mouse", category="Gaming")
    db_session.add(candidate_us)
    db_session.flush()
    offer2 = Offer(product_id=candidate_us.id, merchant_id=merchant.id, price=Decimal("150.00"), mrp=Decimal("150.00"))
    db_session.add(offer2)
    db_session.flush()
    db_session.add(Inventory(offer_id=offer2.id, quantity=10, reorder_level=0))
    db_session.commit()

    engine = RevenueEngine(db_session)
    request = RevenueRecommendationRequest(
        merchant_id=merchant.id,
        customer_id=customer.id,
        primary_product_id=primary.id,
        customer_intent="buy gaming mouse",
        customer_budget=Decimal("200.00")
    )
    
    response = engine.recommend(request)
    assert response.intervention == "UPSELL"
    assert response.recommended_product.id == candidate_us.id
    assert response.score >= 0.55

def test_recommend_alternative_out_of_stock(db_session):
    merchant = Merchant(name="Test Merchant", email="test@merchant.com", is_active=True, currency="INR")
    db_session.add(merchant)
    db_session.flush()

    customer = Customer(merchant_id=merchant.id, name="Test Customer", email="test@test.com")
    db_session.add(customer)
    db_session.flush()

    sku1 = f"M1-{uuid.uuid4().hex[:8]}"
    primary = Product(merchant_id=merchant.id, sku=sku1, name="Gaming Mouse", category="Gaming")
    db_session.add(primary)
    db_session.flush()
    offer1 = Offer(product_id=primary.id, merchant_id=merchant.id, price=Decimal("100.00"), mrp=Decimal("100.00"))
    db_session.add(offer1)
    db_session.flush()
    db_session.add(Inventory(offer_id=offer1.id, quantity=0, reorder_level=0)) # Out of stock

    # Candidate: Alternative Mouse (Gaming)
    sku2 = f"M3-{uuid.uuid4().hex[:8]}"
    candidate_alt = Product(merchant_id=merchant.id, sku=sku2, name="Alt Gaming Mouse", category="Gaming")
    db_session.add(candidate_alt)
    db_session.flush()
    offer2 = Offer(product_id=candidate_alt.id, merchant_id=merchant.id, price=Decimal("90.00"), mrp=Decimal("90.00"))
    db_session.add(offer2)
    db_session.flush()
    db_session.add(Inventory(offer_id=offer2.id, quantity=10, reorder_level=0))
    db_session.commit()

    engine = RevenueEngine(db_session)
    request = RevenueRecommendationRequest(
        merchant_id=merchant.id,
        customer_id=customer.id,
        primary_product_id=primary.id,
        customer_intent="buy gaming mouse",
        customer_budget=Decimal("200.00")
    )
    
    response = engine.recommend(request)
    assert response.intervention == "ALTERNATIVE"
    assert response.recommended_product.id == candidate_alt.id

def test_recommend_none_when_over_budget(db_session):
    merchant = Merchant(name="Test Merchant", email="test@merchant.com", is_active=True, currency="INR")
    db_session.add(merchant)
    db_session.flush()

    customer = Customer(merchant_id=merchant.id, name="Test Customer", email="test@test.com")
    db_session.add(customer)
    db_session.flush()

    sku1 = f"M1-{uuid.uuid4().hex[:8]}"
    primary = Product(merchant_id=merchant.id, sku=sku1, name="Gaming Mouse", category="Gaming")
    db_session.add(primary)
    db_session.flush()
    offer1 = Offer(product_id=primary.id, merchant_id=merchant.id, price=Decimal("100.00"), mrp=Decimal("100.00"))
    db_session.add(offer1)
    db_session.flush()
    db_session.add(Inventory(offer_id=offer1.id, quantity=10, reorder_level=0))

    sku2 = f"M2-{uuid.uuid4().hex[:8]}"
    candidate_us = Product(merchant_id=merchant.id, sku=sku2, name="Pro Gaming Mouse", category="Gaming")
    db_session.add(candidate_us)
    db_session.flush()
    offer2 = Offer(product_id=candidate_us.id, merchant_id=merchant.id, price=Decimal("150.00"), mrp=Decimal("150.00"))
    db_session.add(offer2)
    db_session.flush()
    db_session.add(Inventory(offer_id=offer2.id, quantity=10, reorder_level=0))
    db_session.commit()

    engine = RevenueEngine(db_session)
    request = RevenueRecommendationRequest(
        merchant_id=merchant.id,
        customer_id=customer.id,
        primary_product_id=primary.id,
        customer_intent="buy gaming mouse",
        customer_budget=Decimal("120.00")
    )
    
    response = engine.recommend(request)
    assert response.intervention == "NONE"

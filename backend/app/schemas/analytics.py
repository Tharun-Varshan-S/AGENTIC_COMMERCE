from typing import List, Optional
from uuid import UUID
from datetime import date
from pydantic import BaseModel, ConfigDict
from decimal import Decimal

class KPIStats(BaseModel):
    total_revenue: Decimal
    ai_revenue: Decimal
    total_orders: int
    ai_orders: int
    active_products: int
    low_stock_products: int
    ai_aov: Decimal
    recommendation_conversion: float

class ExpectedRealizedRevenue(BaseModel):
    expected_revenue: Decimal
    realized_revenue: Decimal
    opportunity_converted_percent: float

class RevenueFunnel(BaseModel):
    customer_intent: int
    products_discovered: int
    recommendations_made: int
    recommendations_accepted: int
    added_to_cart: int
    checkout_started: int
    paid_orders: int

class RecommendationAnalytics(BaseModel):
    cross_sell_count: int
    cross_sell_revenue: Decimal
    upsell_count: int
    upsell_revenue: Decimal
    alternative_count: int
    alternative_revenue: Decimal

class TopRecommendation(BaseModel):
    primary_product: str
    recommended_product: str
    intervention_type: str
    score: float
    expected_order_value: Decimal

class PolicyAnalytics(BaseModel):
    allowed: int
    consent_required: int
    rejected: int
    rejection_reasons: dict

class ConsentAnalytics(BaseModel):
    requests: int
    approved: int
    declined: int
    expired: int
    approval_rate: float

class PaymentAnalytics(BaseModel):
    captured: int
    failed: int
    pending: int
    success_rate: float

class RevenueDataPoint(BaseModel):
    date: date
    direct_revenue: Decimal
    ai_revenue: Decimal

class OrderDataPoint(BaseModel):
    date: date
    direct_orders: int
    ai_orders: int

class RevenueIntelligenceKPIs(BaseModel):
    total_recommendations: int
    accepted_recommendations: int
    conversion_rate: float
    additional_revenue: Decimal

class DashboardData(BaseModel):
    kpis: KPIStats
    expected_vs_realized: ExpectedRealizedRevenue
    funnel: RevenueFunnel
    recommendations: RecommendationAnalytics
    top_recommendations: List[TopRecommendation]
    policy: PolicyAnalytics
    consent: ConsentAnalytics
    payment: PaymentAnalytics
    revenue_chart: List[RevenueDataPoint]
    orders_chart: List[OrderDataPoint]
    revenue_intelligence: RevenueIntelligenceKPIs

class RecentOrder(BaseModel):
    id: UUID
    order_number: str
    status: str
    source: str
    total: Decimal
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class RecentDecision(BaseModel):
    id: UUID
    customer_name: str
    intent: str
    primary_product: str
    recommended_product: str
    intervention_type: str
    score: float
    expected_order_value: Decimal
    reason: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class RecentActivity(BaseModel):
    recent_orders: List[RecentOrder]
    recent_decisions: List[RecentDecision]

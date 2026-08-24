from typing import List, Optional
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
    revenue_chart: List[RevenueDataPoint]
    orders_chart: List[OrderDataPoint]
    revenue_intelligence: RevenueIntelligenceKPIs

class RecentOrder(BaseModel):
    order_number: str
    status: str
    source: str
    total: Decimal
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class RecentDecision(BaseModel):
    intent: str
    reason: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class RecentActivity(BaseModel):
    recent_orders: List[RecentOrder]
    recent_decisions: List[RecentDecision]

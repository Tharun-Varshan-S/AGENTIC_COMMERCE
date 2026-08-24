from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from datetime import datetime, timedelta
from decimal import Decimal

from app.models.order import Order
from app.models.product import Product, Inventory
from app.models.agent import AgentDecision
from app.schemas.analytics import DashboardData, KPIStats, RevenueDataPoint, OrderDataPoint, RecentActivity, RecentOrder, RecentDecision, RevenueIntelligenceKPIs

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_data(self, merchant_id: str) -> DashboardData:
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        
        # 1. KPIs
        orders = self.db.scalars(
            select(Order)
            .filter(Order.merchant_id == merchant_id, Order.created_at >= seven_days_ago)
        ).all()

        total_revenue = Decimal('0.00')
        ai_revenue = Decimal('0.00')
        total_orders = len(orders)
        ai_orders = 0

        for order in orders:
            if order.status in ["PAID", "COMPLETED", "PENDING", "CONFIRMED"]:
                total_revenue += order.total
                if order.source == "AI":
                    ai_revenue += order.total
                    ai_orders += 1

        active_products = self.db.scalar(
            select(func.count(Product.id))
            .filter(Product.merchant_id == merchant_id, Product.is_active == True)
        ) or 0

        low_stock_products = self.db.scalar(
            select(func.count(Inventory.id))
            .join(Product)
            .filter(Product.merchant_id == merchant_id, Inventory.quantity <= Inventory.reorder_level)
        ) or 0

        kpis = KPIStats(
            total_revenue=total_revenue,
            ai_revenue=ai_revenue,
            total_orders=total_orders,
            ai_orders=ai_orders,
            active_products=active_products,
            low_stock_products=low_stock_products
        )

        # 2. Charts (Revenue and Orders by Day for last 7 days)
        # Initialize charts with 0s
        revenue_chart_map = {}
        orders_chart_map = {}
        for i in range(7):
            day = (now - timedelta(days=i)).date()
            revenue_chart_map[day] = {"direct": Decimal('0.00'), "ai": Decimal('0.00')}
            orders_chart_map[day] = {"direct": 0, "ai": 0}

        for order in orders:
            if order.status in ["PAID", "COMPLETED", "PENDING", "CONFIRMED"]:
                day = order.created_at.date()
                if day in revenue_chart_map:
                    if order.source == "AI":
                        revenue_chart_map[day]["ai"] += order.total
                        orders_chart_map[day]["ai"] += 1
                    else:
                        revenue_chart_map[day]["direct"] += order.total
                        orders_chart_map[day]["direct"] += 1

        revenue_chart = []
        orders_chart = []
        # Sort by date ascending
        for day in sorted(revenue_chart_map.keys()):
            revenue_chart.append(RevenueDataPoint(
                date=day,
                direct_revenue=revenue_chart_map[day]["direct"],
                ai_revenue=revenue_chart_map[day]["ai"]
            ))
            orders_chart.append(OrderDataPoint(
                date=day,
                direct_orders=orders_chart_map[day]["direct"],
                ai_orders=orders_chart_map[day]["ai"]
            ))

        # 3. Revenue Intelligence
        decisions = self.db.scalars(
            select(AgentDecision)
            .filter(AgentDecision.merchant_id == merchant_id, AgentDecision.created_at >= seven_days_ago)
        ).all()

        total_recommendations = len(decisions)
        
        # Determine accepted recommendations based on orders that have items matching recommended_product_id
        # For simplicity in MVP, we look for orders tagged with source="AI" and just count AI orders as "accepted"
        # Or better: check if AI orders include the recommended items.
        # But for MVP, `ai_orders` is exactly when they accepted the AI flow.
        accepted_recommendations = ai_orders
        
        conversion_rate = 0.0
        if total_recommendations > 0:
            conversion_rate = (accepted_recommendations / total_recommendations) * 100

        # Additional Revenue (Expected vs Realized)
        # Expected from decisions where intervention != NONE
        additional_revenue = Decimal('0.00')
        for d in decisions:
            if d.intervention_type != "NONE" and d.recommended_product_id:
                # Approximate additional revenue as the price of recommended (for cross-sell) 
                # or diff (for upsell) -> this is stored in expected_order_value or we can re-calculate.
                # Actually, our decisions have expected_order_value = primary_price + additional
                # Let's just use ai_revenue as actual additional revenue realized.
                pass
                
        # For simplicity, AI revenue IS the additional revenue realized from interventions
        additional_revenue = ai_revenue

        ri_kpis = RevenueIntelligenceKPIs(
            total_recommendations=total_recommendations,
            accepted_recommendations=accepted_recommendations,
            conversion_rate=conversion_rate,
            additional_revenue=additional_revenue
        )

        return DashboardData(
            kpis=kpis,
            revenue_chart=revenue_chart,
            orders_chart=orders_chart,
            revenue_intelligence=ri_kpis
        )

    def get_recent_activity(self, merchant_id: str) -> RecentActivity:
        recent_orders_db = self.db.scalars(
            select(Order)
            .filter(Order.merchant_id == merchant_id)
            .order_by(Order.created_at.desc())
            .limit(5)
        ).all()

        recent_decisions_db = self.db.scalars(
            select(AgentDecision)
            .filter(AgentDecision.merchant_id == merchant_id)
            .order_by(AgentDecision.created_at.desc())
            .limit(5)
        ).all()

        return RecentActivity(
            recent_orders=[
                RecentOrder(
                    order_number=o.order_number,
                    status=o.status,
                    source=o.source,
                    total=o.total,
                    created_at=o.created_at.isoformat()
                ) for o in recent_orders_db
            ],
            recent_decisions=[
                RecentDecision(
                    intent=d.intent,
                    reason=d.reason or "",
                    created_at=d.created_at.isoformat()
                ) for d in recent_decisions_db
            ]
        )

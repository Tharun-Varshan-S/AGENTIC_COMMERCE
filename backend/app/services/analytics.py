from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta, date
from decimal import Decimal

from app.models.order import Order, Cart
from app.models.product import Product, Inventory
from app.models.agent import AgentDecision
from app.models.audit import AuditLog
from app.models.consent import ConsentRequest
from app.models.order import Payment
from app.schemas.analytics import (
    DashboardData, KPIStats, RevenueDataPoint, OrderDataPoint, 
    RecentActivity, RecentOrder, RecentDecision, RevenueIntelligenceKPIs,
    ExpectedRealizedRevenue, RevenueFunnel, RecommendationAnalytics,
    TopRecommendation, PolicyAnalytics, ConsentAnalytics, PaymentAnalytics
)

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_dashboard_data(self, merchant_id: str) -> DashboardData:
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        
        # Base Data Queries
        orders = self.db.scalars(
            select(Order)
            .filter(Order.merchant_id == merchant_id, Order.created_at >= seven_days_ago)
        ).all()

        decisions = self.db.scalars(
            select(AgentDecision)
            .filter(AgentDecision.merchant_id == merchant_id, AgentDecision.created_at >= seven_days_ago)
        ).all()

        audit_logs = self.db.scalars(
            select(AuditLog)
            .filter(AuditLog.merchant_id == merchant_id, AuditLog.created_at >= seven_days_ago)
        ).all()

        consent_reqs = self.db.scalars(
            select(ConsentRequest)
            .filter(ConsentRequest.merchant_id == merchant_id, ConsentRequest.created_at >= seven_days_ago)
        ).all()

        payments = self.db.scalars(
            select(Payment)
            .join(Order)
            .filter(Order.merchant_id == merchant_id, Payment.created_at >= seven_days_ago)
        ).all()

        # 1. KPIs & Expected vs Realized Revenue
        total_revenue = Decimal('0.00')
        ai_revenue = Decimal('0.00')
        total_orders = len(orders)
        ai_orders = 0

        for order in orders:
            if order.status == "PAID":
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

        expected_revenue = sum([d.expected_order_value for d in decisions if d.expected_order_value], Decimal('0.00'))
        
        kpis = KPIStats(
            total_revenue=total_revenue,
            ai_revenue=ai_revenue,
            total_orders=total_orders,
            ai_orders=ai_orders,
            active_products=active_products,
            low_stock_products=low_stock_products,
            ai_aov=ai_revenue / ai_orders if ai_orders > 0 else Decimal('0.00'),
            recommendation_conversion=(ai_orders / len(decisions) * 100) if len(decisions) > 0 else 0.0
        )

        expected_vs_realized = ExpectedRealizedRevenue(
            expected_revenue=expected_revenue,
            realized_revenue=ai_revenue,
            opportunity_converted_percent=(float(ai_revenue) / float(expected_revenue) * 100) if expected_revenue > 0 else 0.0
        )

        # 2. Charts (Revenue and Orders)
        revenue_chart_map = {}
        orders_chart_map = {}
        for i in range(7):
            day = (now - timedelta(days=i)).date()
            revenue_chart_map[day] = {"direct": Decimal('0.00'), "ai": Decimal('0.00')}
            orders_chart_map[day] = {"direct": 0, "ai": 0}

        for order in orders:
            if order.status == "PAID":
                day = order.created_at.date()
                if day in revenue_chart_map:
                    if order.source == "AI":
                        revenue_chart_map[day]["ai"] += order.total
                        orders_chart_map[day]["ai"] += 1
                    else:
                        revenue_chart_map[day]["direct"] += order.total
                        orders_chart_map[day]["direct"] += 1

        revenue_chart = [RevenueDataPoint(date=day, direct_revenue=revenue_chart_map[day]["direct"], ai_revenue=revenue_chart_map[day]["ai"]) for day in sorted(revenue_chart_map.keys())]
        orders_chart = [OrderDataPoint(date=day, direct_orders=orders_chart_map[day]["direct"], ai_orders=orders_chart_map[day]["ai"]) for day in sorted(revenue_chart_map.keys())]

        # 3. AI Revenue Funnel
        intents = set()
        discovered = set()
        recommended = set()
        accepted = set()
        cart_added = set()
        checkout = set()
        
        for log in audit_logs:
            if log.event_type == "INTENT_RECEIVED":
                intents.add(log.customer_id)
            elif log.event_type == "PRODUCT_DISCOVERED":
                discovered.add(log.customer_id)
            elif log.event_type == "RECOMMENDATION_MADE":
                recommended.add(log.customer_id)
            elif log.event_type == "RECOMMENDATION_ACCEPTED":
                accepted.add(log.customer_id)
            elif log.event_type == "CART_UPDATED":
                cart_added.add(log.customer_id)
            elif log.event_type == "CHECKOUT_STARTED":
                checkout.add(log.customer_id)

        funnel = RevenueFunnel(
            customer_intent=len(intents),
            products_discovered=len(discovered),
            recommendations_made=len(recommended),
            recommendations_accepted=len(accepted),
            added_to_cart=len(cart_added),
            checkout_started=len(checkout),
            paid_orders=ai_orders
        )

        # 4. Recommendation Analytics
        cs_count, cs_rev = 0, Decimal('0.00')
        up_count, up_rev = 0, Decimal('0.00')
        alt_count, alt_rev = 0, Decimal('0.00')

        for d in decisions:
            if d.intervention_type == "CROSS_SELL":
                cs_count += 1
                cs_rev += (d.expected_order_value or Decimal('0'))
            elif d.intervention_type == "UPSELL":
                up_count += 1
                up_rev += (d.expected_order_value or Decimal('0'))
            elif d.intervention_type == "ALTERNATIVE":
                alt_count += 1
                alt_rev += (d.expected_order_value or Decimal('0'))

        rec_analytics = RecommendationAnalytics(
            cross_sell_count=cs_count, cross_sell_revenue=cs_rev,
            upsell_count=up_count, upsell_revenue=up_rev,
            alternative_count=alt_count, alternative_revenue=alt_rev
        )

        # 5. Top Recommendations
        top_recs = []
        sorted_decisions = sorted([d for d in decisions if d.primary_product and d.recommended_product], key=lambda x: x.expected_order_value or 0, reverse=True)[:5]
        for d in sorted_decisions:
            top_recs.append(TopRecommendation(
                primary_product=d.primary_product.name,
                recommended_product=d.recommended_product.name,
                intervention_type=d.intervention_type,
                score=float(d.score) if d.score else 0.0,
                expected_order_value=d.expected_order_value or Decimal('0')
            ))

        # 6. Policy Analytics
        allowed = 0
        consent_req = 0
        rejected = 0
        reasons = {}

        for log in audit_logs:
            if log.event_type == "POLICY_EVALUATED":
                meta = log.metadata_json or {}
                decision = meta.get("decision", "")
                reason = meta.get("reason", "")
                if decision == "ALLOWED":
                    allowed += 1
                elif decision == "REQUIRES_CONSENT":
                    consent_req += 1
                elif decision == "REJECTED":
                    rejected += 1
                    reasons[reason] = reasons.get(reason, 0) + 1

        policy = PolicyAnalytics(
            allowed=allowed,
            consent_required=consent_req,
            rejected=rejected,
            rejection_reasons=reasons
        )

        # 7. Consent Analytics
        consent = ConsentAnalytics(
            requests=len(consent_reqs),
            approved=len([c for c in consent_reqs if c.status == "APPROVED"]),
            declined=len([c for c in consent_reqs if c.status == "DECLINED"]),
            expired=len([c for c in consent_reqs if c.status == "EXPIRED"]),
            approval_rate=(len([c for c in consent_reqs if c.status == "APPROVED"]) / len(consent_reqs) * 100) if len(consent_reqs) > 0 else 0.0
        )

        # 8. Payment Analytics
        payment = PaymentAnalytics(
            captured=len([p for p in payments if p.status == "CAPTURED"]),
            failed=len([p for p in payments if p.status == "FAILED"]),
            pending=len([p for p in payments if p.status == "CREATED" or p.status == "AUTHORIZED"]),
            success_rate=(len([p for p in payments if p.status == "CAPTURED"]) / len(payments) * 100) if len(payments) > 0 else 0.0
        )

        # 9. Legacy RI KPIs
        ri_kpis = RevenueIntelligenceKPIs(
            total_recommendations=len(decisions),
            accepted_recommendations=ai_orders,
            conversion_rate=kpis.recommendation_conversion,
            additional_revenue=ai_revenue
        )

        return DashboardData(
            kpis=kpis,
            expected_vs_realized=expected_vs_realized,
            funnel=funnel,
            recommendations=rec_analytics,
            top_recommendations=top_recs,
            policy=policy,
            consent=consent,
            payment=payment,
            revenue_chart=revenue_chart,
            orders_chart=orders_chart,
            revenue_intelligence=ri_kpis
        )

    def get_recent_activity(self, merchant_id: str) -> RecentActivity:
        recent_orders_db = self.db.scalars(
            select(Order)
            .filter(Order.merchant_id == merchant_id)
            .order_by(Order.created_at.desc())
            .limit(50)
        ).all()

        recent_decisions_db = self.db.scalars(
            select(AgentDecision)
            .filter(AgentDecision.merchant_id == merchant_id)
            .order_by(AgentDecision.created_at.desc())
            .limit(50)
        ).all()

        return RecentActivity(
            recent_orders=[
                RecentOrder(
                    id=o.id,
                    order_number=o.order_number,
                    status=o.status,
                    source=o.source,
                    total=o.total,
                    created_at=o.created_at.isoformat()
                ) for o in recent_orders_db
            ],
            recent_decisions=[
                RecentDecision(
                    id=d.id,
                    customer_name=d.customer.name if d.customer else "Unknown",
                    intent=d.intent or "UNKNOWN",
                    primary_product=d.primary_product.name if d.primary_product else "N/A",
                    recommended_product=d.recommended_product.name if d.recommended_product else "N/A",
                    intervention_type=d.intervention_type or "NONE",
                    score=float(d.score) if d.score else 0.0,
                    expected_order_value=d.expected_order_value or Decimal('0.00'),
                    reason=d.reason or "",
                    created_at=d.created_at.isoformat()
                ) for d in recent_decisions_db
            ]
        )

    def get_activity_feed(self, merchant_id: str) -> List[Dict[str, Any]]:
        logs = self.db.scalars(
            select(AuditLog)
            .filter(AuditLog.merchant_id == merchant_id)
            .order_by(AuditLog.created_at.desc())
            .limit(100)
        ).all()

        return [
            {
                "id": log.id,
                "event_type": log.event_type,
                "actor_type": log.actor_type,
                "action": log.action,
                "metadata": log.metadata_json,
                "created_at": log.created_at.isoformat()
            } for log in logs
        ]

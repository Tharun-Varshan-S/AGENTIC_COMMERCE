"use client";

import { useEffect, useState } from "react";
import { fetchDashboard, fetchRecentActivity, fetchPromotions } from "@/lib/api";
import { 
  TrendingUp, ShoppingCart, Package, AlertTriangle, Bot,
  Target, ShieldCheck, ShieldAlert, CreditCard, Activity,
  Megaphone
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar
} from "recharts";

function formatCurrency(amount: string | number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0
  }).format(Number(amount));
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' });
}

function formatTime(dateString: string) {
  return new Date(dateString).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
}

export default function Dashboard() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [activity, setActivity] = useState<any>(null);
  const [promotions, setPromotions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [dashData, actData, promosData] = await Promise.all([
          fetchDashboard(), fetchRecentActivity(), fetchPromotions()
        ]);
        setDashboard(dashData);
        setActivity(actData);
        setPromotions(promosData);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"></div>
      </div>
    );
  }

  if (!dashboard) {
    return <div className="text-red-500">Failed to load dashboard data. Ensure backend is running.</div>;
  }

  const { kpis, expected_vs_realized, funnel, recommendations, top_recommendations, policy, consent, payment, revenue_chart, orders_chart } = dashboard;
  
  const formattedRevenueChart = revenue_chart.map((d: any) => ({
    ...d, date: formatDate(d.date), direct: Number(d.direct_revenue), ai: Number(d.ai_revenue)
  }));

  const formattedOrdersChart = orders_chart.map((d: any) => ({
    ...d, date: formatDate(d.date), direct: Number(d.direct_orders), ai: Number(d.ai_orders)
  }));

  const recommendationChartData = [
    { name: "Cross-Sell", count: recommendations.cross_sell_count, revenue: recommendations.cross_sell_revenue },
    { name: "Upsell", count: recommendations.upsell_count, revenue: recommendations.upsell_revenue },
    { name: "Alternative", count: recommendations.alternative_count, revenue: recommendations.alternative_revenue }
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      
      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-500">AI Revenue (7d)</h3>
            <Bot className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="mt-2 flex flex-col gap-1">
            <span className="text-2xl font-semibold text-slate-900">{formatCurrency(kpis.ai_revenue)}</span>
            <span className="text-sm font-medium text-slate-500">Total: {formatCurrency(kpis.total_revenue)}</span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-500">AI Orders (7d)</h3>
            <ShoppingCart className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-2 flex flex-col gap-1">
            <span className="text-2xl font-semibold text-slate-900">{kpis.ai_orders}</span>
            <span className="text-sm font-medium text-slate-500">Total: {kpis.total_orders}</span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-500">AI AOV</h3>
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          </div>
          <div className="mt-2 flex flex-col gap-1">
            <span className="text-2xl font-semibold text-slate-900">{formatCurrency(kpis.ai_aov)}</span>
          </div>
        </div>

        <div className="bg-indigo-50 rounded-xl border border-indigo-100 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-indigo-600">Rec. Conversion</h3>
            <Target className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-indigo-900">{kpis.recommendation_conversion.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Analytics Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Expected vs Realized */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4">Opportunity Conversion</h3>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-slate-500">Expected Revenue (Identified)</p>
              <p className="text-xl font-medium text-slate-900">{formatCurrency(expected_vs_realized.expected_revenue)}</p>
            </div>
            <div>
              <p className="text-sm text-slate-500">Realized Revenue (Captured)</p>
              <p className="text-xl font-medium text-emerald-600">{formatCurrency(expected_vs_realized.realized_revenue)}</p>
            </div>
            <div className="pt-2 border-t border-slate-100">
              <p className="text-sm text-slate-500">Converted %</p>
              <p className="text-xl font-bold text-indigo-600">{expected_vs_realized.opportunity_converted_percent.toFixed(1)}%</p>
            </div>
          </div>
        </div>

        {/* AI Revenue Funnel */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 lg:col-span-2">
          <h3 className="text-base font-semibold text-slate-800 mb-4">AI Revenue Funnel</h3>
          <div className="flex justify-between items-end h-40 pb-6 px-4">
            <FunnelStep label="Intent" value={funnel.customer_intent} max={funnel.customer_intent} color="bg-slate-200" />
            <FunnelStep label="Discovered" value={funnel.products_discovered} max={funnel.customer_intent} color="bg-slate-300" />
            <FunnelStep label="Recommended" value={funnel.recommendations_made} max={funnel.customer_intent} color="bg-indigo-200" />
            <FunnelStep label="Accepted" value={funnel.recommendations_accepted} max={funnel.customer_intent} color="bg-indigo-400" />
            <FunnelStep label="Cart" value={funnel.added_to_cart} max={funnel.customer_intent} color="bg-indigo-500" />
            <FunnelStep label="Checkout" value={funnel.checkout_started} max={funnel.customer_intent} color="bg-emerald-400" />
            <FunnelStep label="Paid" value={funnel.paid_orders} max={funnel.customer_intent} color="bg-emerald-600" />
          </div>
        </div>
      </div>

      {/* Analytics Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Recommendation Analytics */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4">Intervention Type</h3>
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={recommendationChartData} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tick={{fontSize: 12}} />
                <YAxis tick={{fontSize: 12}} />
                <Tooltip />
                <Bar dataKey="count" fill="#6366f1" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Policy & Consent & Payments */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 lg:col-span-2">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2"><ShieldCheck className="w-4 h-4 text-emerald-500"/> Policy Monitor</h3>
              <div className="mt-3 space-y-2 text-sm text-slate-600">
                <div className="flex justify-between"><span>Allowed:</span> <span className="font-medium">{policy.allowed}</span></div>
                <div className="flex justify-between"><span>Consent Required:</span> <span className="font-medium">{policy.consent_required}</span></div>
                <div className="flex justify-between"><span>Rejected:</span> <span className="font-medium text-red-500">{policy.rejected}</span></div>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2"><ShieldAlert className="w-4 h-4 text-amber-500"/> Consent Analytics</h3>
              <div className="mt-3 space-y-2 text-sm text-slate-600">
                <div className="flex justify-between"><span>Requests:</span> <span className="font-medium">{consent.requests}</span></div>
                <div className="flex justify-between"><span>Approved:</span> <span className="font-medium text-emerald-600">{consent.approved}</span></div>
                <div className="flex justify-between"><span>Declined:</span> <span className="font-medium text-red-500">{consent.declined}</span></div>
                <div className="flex justify-between"><span>Rate:</span> <span className="font-medium text-indigo-600">{consent.approval_rate.toFixed(1)}%</span></div>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2"><CreditCard className="w-4 h-4 text-blue-500"/> Payments</h3>
              <div className="mt-3 space-y-2 text-sm text-slate-600">
                <div className="flex justify-between"><span>Captured:</span> <span className="font-medium text-emerald-600">{payment.captured}</span></div>
                <div className="flex justify-between"><span>Failed:</span> <span className="font-medium text-red-500">{payment.failed}</span></div>
                <div className="flex justify-between"><span>Pending:</span> <span className="font-medium">{payment.pending}</span></div>
                <div className="flex justify-between"><span>Success:</span> <span className="font-medium text-indigo-600">{payment.success_rate.toFixed(1)}%</span></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Top Recommendations */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
          <h3 className="text-base font-semibold text-slate-800">Top AI Recommendations</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-slate-500 bg-slate-50 border-b border-slate-200 uppercase">
              <tr>
                <th className="px-5 py-3 font-medium">Primary Product</th>
                <th className="px-5 py-3 font-medium">Recommended</th>
                <th className="px-5 py-3 font-medium">Type</th>
                <th className="px-5 py-3 font-medium">Score</th>
                <th className="px-5 py-3 font-medium text-right">Expected Value</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {top_recommendations.map((rec: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-3 font-medium text-slate-900">{rec.primary_product}</td>
                  <td className="px-5 py-3 text-indigo-600">{rec.recommended_product}</td>
                  <td className="px-5 py-3">
                    <span className="text-xs font-medium bg-slate-100 px-2 py-0.5 rounded-full">{rec.intervention_type}</span>
                  </td>
                  <td className="px-5 py-3 text-slate-500">{rec.score.toFixed(2)}</td>
                  <td className="px-5 py-3 text-right font-medium text-emerald-600">{formatCurrency(rec.expected_order_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Promotions & Ads */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mt-6">
        <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-indigo-50/50">
          <div className="flex items-center gap-2">
             <Megaphone className="w-5 h-5 text-indigo-600" />
             <h3 className="text-base font-semibold text-indigo-900">Active AI Promotions & Ads</h3>
          </div>
          <button className="text-sm font-medium text-indigo-600 hover:text-indigo-700 bg-white border border-indigo-200 px-3 py-1.5 rounded-md shadow-sm">
            Create Campaign
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-slate-500 bg-slate-50 border-b border-slate-200 uppercase">
              <tr>
                <th className="px-5 py-3 font-medium">Product</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Priority</th>
                <th className="px-5 py-3 font-medium text-right">Budget</th>
                <th className="px-5 py-3 font-medium text-right">Remaining</th>
                <th className="px-5 py-3 font-medium text-right">Performance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {promotions.map((promo: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-4 font-medium text-slate-900">{promo.product_name}</td>
                  <td className="px-5 py-4">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${promo.status === 'ACTIVE' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                      {promo.status}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex gap-0.5">
                       {Array.from({length: 5}).map((_, i) => (
                          <div key={i} className={`w-1.5 h-3 rounded-sm ${i < promo.priority ? 'bg-indigo-500' : 'bg-slate-200'}`} />
                       ))}
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right font-medium">{formatCurrency(promo.budget)}</td>
                  <td className="px-5 py-4 text-right">
                    <div className="flex flex-col items-end gap-1">
                      <span className="font-medium text-slate-900">{formatCurrency(promo.remaining_budget)}</span>
                      <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <div className="h-full bg-indigo-500" style={{width: `${(promo.remaining_budget / promo.budget) * 100}%`}}></div>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-right">
                    <div className="text-xs text-slate-500 space-y-0.5">
                      <div><span className="font-medium text-slate-700">{promo.impressions}</span> views</div>
                      <div><span className="font-medium text-slate-700">{promo.clicks}</span> clicks</div>
                      <div><span className="font-medium text-emerald-600">{promo.conversions}</span> sales</div>
                    </div>
                  </td>
                </tr>
              ))}
              {promotions.length === 0 && (
                <tr>
                   <td colSpan={6} className="px-5 py-8 text-center text-slate-500">
                     No active promotions. Run the seed script to generate sample promotions.
                   </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}

function FunnelStep({ label, value, max, color }: { label: string, value: number, max: number, color: string }) {
  const height = max > 0 ? (value / max) * 100 : 0;
  return (
    <div className="flex flex-col items-center gap-2 group w-full px-1">
      <span className="text-sm font-bold text-slate-700">{value}</span>
      <div className="w-full flex justify-center items-end h-full">
        <div className={`w-full rounded-t-sm transition-all duration-300 ${color}`} style={{ height: `${Math.max(height, 5)}%` }}></div>
      </div>
      <span className="text-xs text-slate-500 text-center">{label}</span>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { fetchDashboard, fetchRecentActivity } from "@/lib/api";
import { 
  TrendingUp, 
  ShoppingCart, 
  Package, 
  AlertTriangle,
  Bot,
  ArrowUpRight,
  ArrowDownRight
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend
} from "recharts";

function formatCurrency(amount: string | number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(Number(amount));
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-IN', {
    month: 'short',
    day: 'numeric'
  });
}

function formatTime(dateString: string) {
  return new Date(dateString).toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit'
  });
}

export default function Dashboard() {
  const [dashboard, setDashboard] = useState<any>(null);
  const [activity, setActivity] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [dashData, actData] = await Promise.all([
          fetchDashboard(),
          fetchRecentActivity()
        ]);
        setDashboard(dashData);
        setActivity(actData);
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

  const { kpis, revenue_chart, orders_chart } = dashboard;
  const aiRevenuePercentage = kpis.total_revenue > 0 ? (kpis.ai_revenue / kpis.total_revenue) * 100 : 0;
  
  // Format chart data for Recharts
  const formattedRevenueChart = revenue_chart.map((d: any) => ({
    ...d,
    date: formatDate(d.date),
    direct: Number(d.direct_revenue),
    ai: Number(d.ai_revenue)
  }));

  const formattedOrdersChart = orders_chart.map((d: any) => ({
    ...d,
    date: formatDate(d.date),
    direct: Number(d.direct_orders),
    ai: Number(d.ai_orders)
  }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      
      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-500">Total Revenue (7d)</h3>
            <TrendingUp className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-slate-900">{formatCurrency(kpis.total_revenue)}</span>
          </div>
        </div>

        <div className="bg-indigo-50 rounded-xl border border-indigo-100 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-indigo-600">AI-Assisted Revenue</h3>
            <Bot className="h-4 w-4 text-indigo-500" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-indigo-900">{formatCurrency(kpis.ai_revenue)}</span>
            <span className="text-sm font-medium text-indigo-600 bg-indigo-100 px-2 py-0.5 rounded-full">
              {aiRevenuePercentage.toFixed(1)}% of total
            </span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-500">Orders (7d)</h3>
            <ShoppingCart className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-semibold text-slate-900">{kpis.total_orders}</span>
            <span className="text-sm font-medium text-slate-500">
              ({kpis.ai_orders} AI)
            </span>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-medium text-slate-500">Active Products</h3>
            <Package className="h-4 w-4 text-slate-400" />
          </div>
          <div className="mt-2 flex items-center gap-2">
            <span className="text-2xl font-semibold text-slate-900">{kpis.active_products}</span>
            {kpis.low_stock_products > 0 && (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full">
                <AlertTriangle className="h-3 w-3" />
                {kpis.low_stock_products} Low Stock
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Revenue Chart */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4">Revenue Breakdown</h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={formattedRevenueChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorAi" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorDirect" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#94a3b8" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} tickFormatter={(val) => `₹${val/1000}k`} />
                <Tooltip 
                  formatter={(value: any) => formatCurrency(Number(value))}
                  contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}
                />
                <Legend iconType="circle" wrapperStyle={{paddingTop: '20px'}} />
                <Area type="monotone" dataKey="ai" name="AI Revenue" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorAi)" />
                <Area type="monotone" dataKey="direct" name="Direct Revenue" stroke="#94a3b8" strokeWidth={2} fillOpacity={1} fill="url(#colorDirect)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Orders Chart */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5">
          <h3 className="text-base font-semibold text-slate-800 mb-4">Order Volume</h3>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={formattedOrdersChart} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} dy={10} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} allowDecimals={false} />
                <Tooltip
                  formatter={(value: any) => value}
                  contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}
                />
                <Legend iconType="circle" wrapperStyle={{paddingTop: '20px'}} />
                <Bar dataKey="ai" name="AI Orders" stackId="a" fill="#818cf8" radius={[0, 0, 4, 4]} />
                <Bar dataKey="direct" name="Direct Orders" stackId="a" fill="#cbd5e1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      {activity && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          
          {/* Recent Orders */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h3 className="text-base font-semibold text-slate-800">Recent Orders</h3>
              <a href="#" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">View all</a>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-slate-500 bg-slate-50 border-b border-slate-200 uppercase">
                  <tr>
                    <th className="px-5 py-3 font-medium">Order</th>
                    <th className="px-5 py-3 font-medium">Source</th>
                    <th className="px-5 py-3 font-medium">Amount</th>
                    <th className="px-5 py-3 font-medium text-right">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {activity.recent_orders.map((order: any, idx: number) => (
                    <tr key={idx} className="hover:bg-slate-50 transition-colors">
                      <td className="px-5 py-3 font-medium text-slate-900">{order.order_number}</td>
                      <td className="px-5 py-3">
                        {order.source === 'AI' ? (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full">
                            <Bot className="h-3 w-3" /> AI
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 bg-slate-100 px-2 py-0.5 rounded-full">
                            Direct
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-3 font-medium">{formatCurrency(order.total)}</td>
                      <td className="px-5 py-3 text-right text-slate-500 whitespace-nowrap">
                        {formatDate(order.created_at)} {formatTime(order.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* AI Decisions Log */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
            <div className="p-5 border-b border-slate-100 flex justify-between items-center bg-slate-50/50">
              <h3 className="text-base font-semibold text-slate-800">Recent AI Decisions</h3>
              <a href="#" className="text-sm font-medium text-indigo-600 hover:text-indigo-700">View log</a>
            </div>
            <div className="p-0 flex-1 overflow-y-auto">
              <ul className="divide-y divide-slate-100">
                {activity.recent_decisions.map((dec: any, idx: number) => (
                  <li key={idx} className="p-5 hover:bg-slate-50 transition-colors">
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 mt-1">
                        <div className="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-600">
                          <Bot className="h-4 w-4" />
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-900 truncate">
                          Intent: {dec.intent.replace('_', ' ')}
                        </p>
                        <p className="text-sm text-slate-500 mt-1 line-clamp-2">
                          {dec.reason}
                        </p>
                      </div>
                      <div className="flex-shrink-0 text-xs text-slate-400 whitespace-nowrap">
                        {formatDate(dec.created_at)}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}

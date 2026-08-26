"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { fetchOrderDetails } from "@/lib/api";
import { ArrowLeft, Clock, ShoppingCart, User, Target, CreditCard, Activity, CheckCircle, Shield, ShieldCheck, Box, Package, ChevronRight, Bot } from "lucide-react";

function formatCurrency(amount: string | number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0
  }).format(Number(amount));
}

function getEventIcon(type: string) {
  if (type.includes('POLICY') || type.includes('CONSENT')) return <Shield className="w-4 h-4 text-amber-500" />;
  if (type.includes('PAYMENT') || type.includes('CHECKOUT')) return <CreditCard className="w-4 h-4 text-emerald-500" />;
  if (type.includes('CART')) return <ShoppingCart className="w-4 h-4 text-blue-500" />;
  if (type.includes('RECOMMENDATION')) return <Target className="w-4 h-4 text-indigo-500" />;
  if (type.includes('PRODUCT') || type.includes('INVENTORY')) return <Box className="w-4 h-4 text-slate-500" />;
  if (type.includes('INTENT')) return <Bot className="w-4 h-4 text-indigo-600" />;
  return <Activity className="w-4 h-4 text-slate-500" />;
}

export default function OrderDetail() {
  const params = useParams();
  const router = useRouter();
  const [order, setOrder] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchOrderDetails(params.id as string);
        setOrder(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex h-[80vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"></div>
      </div>
    );
  }

  if (!order) {
    return (
      <div className="text-center py-20 text-slate-500">
        Order not found
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => router.back()} className="p-2 hover:bg-slate-100 rounded-full transition-colors">
          <ArrowLeft className="w-5 h-5 text-slate-600" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
            {order.order_number}
            <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
              order.status === 'PAID' ? 'bg-emerald-100 text-emerald-700' :
              order.status === 'PENDING' ? 'bg-amber-100 text-amber-700' :
              'bg-slate-100 text-slate-700'
            }`}>
              {order.status}
            </span>
            {order.source === 'AI' && (
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 flex items-center gap-1">
                <Bot className="w-3 h-3" /> AI Generated
              </span>
            )}
          </h1>
          <p className="text-sm text-slate-500 mt-1 flex items-center gap-2">
            <Clock className="w-4 h-4" /> {new Date(order.created_at).toLocaleString()}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Main Details */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center gap-2 bg-slate-50/50">
              <Package className="w-5 h-5 text-slate-400" />
              <h3 className="font-semibold text-slate-800">Order Items</h3>
            </div>
            <div className="divide-y divide-slate-100">
              {order.items.map((item: any) => (
                <div key={item.id} className="p-5 flex items-center justify-between hover:bg-slate-50 transition-colors">
                  <div className="flex gap-4">
                    <div className="w-12 h-12 bg-slate-100 rounded-lg flex items-center justify-center flex-shrink-0">
                      <Box className="w-6 h-6 text-slate-400" />
                    </div>
                    <div>
                      <p className="font-medium text-slate-900">{item.product_name}</p>
                      <p className="text-sm text-slate-500">SKU: {item.sku}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-slate-900">{formatCurrency(item.subtotal)}</p>
                    <p className="text-sm text-slate-500">{item.quantity} x {formatCurrency(item.unit_price)}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="p-5 bg-slate-50/50 border-t border-slate-100 space-y-2">
              <div className="flex justify-between text-sm text-slate-600">
                <span>Subtotal</span>
                <span>{formatCurrency(order.subtotal)}</span>
              </div>
              <div className="flex justify-between text-sm text-slate-600">
                <span>Discount</span>
                <span className="text-emerald-600">-{formatCurrency(order.discount)}</span>
              </div>
              <div className="flex justify-between font-semibold text-slate-900 pt-2 border-t border-slate-200">
                <span>Total</span>
                <span>{formatCurrency(order.total)}</span>
              </div>
            </div>
          </div>
          
          {order.metadata_json?.agent_trace && (
            <div className="bg-indigo-50/50 rounded-xl border border-indigo-100 shadow-sm overflow-hidden">
              <div className="p-5 border-b border-indigo-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="w-5 h-5 text-indigo-500" />
                  <h3 className="font-semibold text-indigo-900">AI Order Attribution</h3>
                </div>
              </div>
              <div className="p-5">
                <pre className="text-xs text-indigo-800 whitespace-pre-wrap font-mono bg-indigo-100/50 p-4 rounded-lg">
                  {JSON.stringify(order.metadata_json.agent_trace, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center gap-2 bg-slate-50/50">
              <User className="w-5 h-5 text-slate-400" />
              <h3 className="font-semibold text-slate-800">Customer</h3>
            </div>
            <div className="p-5">
              <p className="font-medium text-slate-900">{order.customer.name}</p>
              <p className="text-sm text-slate-500">{order.customer.email}</p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center gap-2 bg-slate-50/50">
              <Activity className="w-5 h-5 text-slate-400" />
              <h3 className="font-semibold text-slate-800">Transaction Trace</h3>
            </div>
            <div className="p-5">
              <div className="relative border-l-2 border-slate-100 pl-6 space-y-6">
                {order.trace.map((log: any, i: number) => (
                  <div key={log.id} className="relative">
                    <span className="absolute -left-[33px] flex items-center justify-center w-6 h-6 rounded-full bg-white border border-slate-200 shadow-sm">
                      {getEventIcon(log.event_type)}
                    </span>
                    <div className="flex flex-col gap-0.5">
                      <span className="text-xs font-semibold text-slate-900">{log.event_type.replace(/_/g, ' ')}</span>
                      <span className="text-xs text-slate-500">{log.action}</span>
                      <span className="text-[10px] text-slate-400">{new Date(log.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                ))}
                {order.trace.length === 0 && (
                  <div className="text-xs text-slate-500">No trace found.</div>
                )}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

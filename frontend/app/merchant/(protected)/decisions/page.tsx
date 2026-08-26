"use client";

import { useEffect, useState } from "react";
import { fetchRecentActivity } from "@/lib/api";
import { Bot, Search, Target, TrendingUp, RefreshCcw } from "lucide-react";

function formatCurrency(amount: string | number) {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency', currency: 'INR', maximumFractionDigits: 0
  }).format(Number(amount));
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-IN', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  });
}

function getInterventionIcon(type: string) {
  switch(type) {
    case 'UPSELL': return <TrendingUp className="w-4 h-4 text-indigo-500" />;
    case 'CROSS_SELL': return <Target className="w-4 h-4 text-emerald-500" />;
    case 'ALTERNATIVE': return <RefreshCcw className="w-4 h-4 text-amber-500" />;
    default: return <Bot className="w-4 h-4 text-slate-500" />;
  }
}

export default function AI_Decisions() {
  const [decisions, setDecisions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const actData = await fetchRecentActivity();
        setDecisions(actData.recent_decisions || []);
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
      <div className="flex h-full items-center justify-center pt-20">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-600 border-t-transparent"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">AI Decision Explorer</h1>
          <p className="text-sm text-slate-500 mt-1">Audit log of autonomous recommendations and interventions.</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex gap-4 bg-slate-50/50">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search decisions by customer or intent..." 
              className="w-full pl-9 pr-4 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-slate-500 bg-slate-50 border-b border-slate-200 uppercase">
              <tr>
                <th className="px-5 py-4 font-medium">Time & Customer</th>
                <th className="px-5 py-4 font-medium">Intent</th>
                <th className="px-5 py-4 font-medium">Context (Primary)</th>
                <th className="px-5 py-4 font-medium">Intervention</th>
                <th className="px-5 py-4 font-medium">Score</th>
                <th className="px-5 py-4 font-medium text-right">Expected Lift</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {decisions.map((dec, idx) => (
                <tr key={idx} className="hover:bg-slate-50 transition-colors">
                  <td className="px-5 py-4">
                    <div className="font-medium text-slate-900">{dec.customer_name}</div>
                    <div className="text-xs text-slate-500 mt-1">{formatDate(dec.created_at)}</div>
                  </td>
                  <td className="px-5 py-4 font-medium text-slate-700">
                    {dec.intent.replace('_', ' ').toUpperCase()}
                  </td>
                  <td className="px-5 py-4 text-slate-600">
                    {dec.primary_product}
                  </td>
                  <td className="px-5 py-4">
                    <div className="flex flex-col gap-1">
                      <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-md bg-slate-100 w-fit">
                        {getInterventionIcon(dec.intervention_type)}
                        {dec.intervention_type}
                      </span>
                      <span className="text-indigo-600 font-medium truncate max-w-[200px]" title={dec.recommended_product}>
                        → {dec.recommended_product}
                      </span>
                      <span className="text-xs text-slate-500 mt-1 italic truncate max-w-[250px]" title={dec.reason}>
                        "{dec.reason}"
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-4 text-slate-500">
                    <div className="w-16 bg-slate-100 rounded-full h-1.5 mb-1">
                      <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${dec.score * 100}%` }}></div>
                    </div>
                    {dec.score.toFixed(2)}
                  </td>
                  <td className="px-5 py-4 text-right font-medium text-emerald-600">
                    {dec.expected_order_value > 0 ? `+${formatCurrency(dec.expected_order_value)}` : '-'}
                  </td>
                </tr>
              ))}
              {decisions.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-500">
                    No AI decisions recorded yet.
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

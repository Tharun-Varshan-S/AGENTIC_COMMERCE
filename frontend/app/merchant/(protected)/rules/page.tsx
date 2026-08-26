"use client";

import { useEffect, useState } from "react";
import { fetchMerchantRules } from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { ShieldCheck, Settings, AlertTriangle } from "lucide-react";

function getRuleBadge(type: string) {
  switch (type) {
    case 'DISCOUNT_LIMIT': return 'bg-indigo-100 text-indigo-700 border-indigo-200';
    case 'PROMOTION_APPROVAL': return 'bg-amber-100 text-amber-700 border-amber-200';
    case 'FORBIDDEN_CATEGORY': return 'bg-red-100 text-red-700 border-red-200';
    default: return 'bg-slate-100 text-slate-700 border-slate-200';
  }
}

export default function RulesPage() {
  const { user } = useAuth();
  const [rules, setRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      if (!user?.merchant_id) return;
      try {
        const data = await fetchMerchantRules(user.merchant_id);
        setRules(data || []);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user]);

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
          <h1 className="text-2xl font-bold text-slate-900">Agent Rules & Guardrails</h1>
          <p className="text-sm text-slate-500 mt-1">Configure boundaries and constraints for your autonomous AI agents.</p>
        </div>
        <button className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors">
          <Settings className="w-4 h-4" />
          New Rule
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {rules.map((rule, idx) => (
          <div key={idx} className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex items-start gap-5">
            <div className={`p-3 rounded-xl border ${
              rule.is_active ? 'bg-emerald-50 border-emerald-100 text-emerald-600' : 'bg-slate-50 border-slate-200 text-slate-400'
            }`}>
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-semibold text-slate-900 text-lg">{rule.name}</h3>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium border ${getRuleBadge(rule.rule_type)}`}>
                    {rule.rule_type.replace('_', ' ')}
                  </span>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" checked={rule.is_active} readOnly />
                    <div className="w-9 h-5 bg-slate-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
                  </label>
                </div>
              </div>
              <p className="text-slate-600 text-sm mb-4">{rule.description}</p>
              
              <div className="bg-slate-50 rounded-lg p-4 border border-slate-100 font-mono text-sm overflow-x-auto text-slate-700">
                <span className="text-slate-400 select-none mr-2">{"{"}</span>
                <span className="block pl-4">
                  {Object.entries(rule.parameters_json).map(([key, value], i) => (
                    <div key={key}>
                      <span className="text-indigo-600">"{key}"</span>: {typeof value === 'string' ? `"${value}"` : String(value)}
                      {i < Object.keys(rule.parameters_json).length - 1 ? ',' : ''}
                    </div>
                  ))}
                </span>
                <span className="text-slate-400 select-none">{"}"}</span>
              </div>
            </div>
          </div>
        ))}
        
        {rules.length === 0 && (
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-12 text-center">
            <div className="flex flex-col items-center justify-center">
              <AlertTriangle className="w-12 h-12 text-amber-400 mb-4" />
              <h3 className="text-lg font-medium text-slate-900 mb-1">No guardrails configured</h3>
              <p className="text-slate-500 max-w-sm">Your AI agents currently operate without any specific constraints. Add rules to control discounts, restricted products, and approval flows.</p>
              <button className="mt-6 bg-white border border-slate-300 text-slate-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors">
                Setup Default Rules
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

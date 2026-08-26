"use client";

import { useEffect, useState } from "react";
import { fetchAuditLogs } from "@/lib/api";
import { Activity, Clock, Shield, Search, ShoppingCart, Target, Info, CreditCard, Box, UserCheck } from "lucide-react";

function getEventIcon(type: string) {
  if (type.includes('POLICY') || type.includes('CONSENT')) return <Shield className="w-4 h-4 text-amber-500" />;
  if (type.includes('PAYMENT') || type.includes('CHECKOUT')) return <CreditCard className="w-4 h-4 text-emerald-500" />;
  if (type.includes('CART')) return <ShoppingCart className="w-4 h-4 text-blue-500" />;
  if (type.includes('RECOMMENDATION')) return <Target className="w-4 h-4 text-indigo-500" />;
  if (type.includes('PRODUCT')) return <Box className="w-4 h-4 text-slate-500" />;
  if (type.includes('INTENT')) return <UserCheck className="w-4 h-4 text-emerald-600" />;
  return <Activity className="w-4 h-4 text-slate-500" />;
}

export default function AgentActivity() {
  const [activity, setActivity] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const logs = await fetchAuditLogs();
        setActivity(logs || []);
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
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Agent Activity Timeline</h1>
          <p className="text-sm text-slate-500 mt-1">Live feed of autonomous agent operations and system events.</p>
        </div>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-6">
        <div className="relative border-l-2 border-slate-100 pl-6 space-y-8">
          {activity.map((log, i) => (
            <div key={log.id} className="relative">
              <span className="absolute -left-[35px] flex items-center justify-center w-8 h-8 rounded-full bg-white border border-slate-200 shadow-sm">
                {getEventIcon(log.event_type)}
              </span>
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-900">{log.event_type.replace(/_/g, ' ')}</span>
                  <span className="text-xs font-medium text-slate-500 bg-slate-100 px-2 py-0.5 rounded">{log.actor_type}</span>
                </div>
                <p className="text-sm text-slate-600">{log.action}</p>
                <div className="text-xs text-slate-400 mt-1 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(log.created_at).toLocaleString()}
                </div>
              </div>
            </div>
          ))}
          {activity.length === 0 && (
            <div className="text-center text-slate-500 py-10">No activity logged yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}

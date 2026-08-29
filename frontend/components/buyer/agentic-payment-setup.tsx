import { useState, useEffect } from "react";
import { setupAgenticAuthorization, getAgenticAuthorizationStatus, revokeAgenticAuthorization } from "@/lib/api";

export function AgenticPaymentSetup({ customerId, onStatusChange }: { customerId: string, onStatusChange?: (status: string) => void }) {
  const [status, setStatus] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isConfiguring, setIsConfiguring] = useState(false);
  
  const [perTxLimit, setPerTxLimit] = useState(2000);
  const [dailyLimit, setDailyLimit] = useState(10000);
  
  useEffect(() => {
    if (customerId) {
      fetchStatus();
    }
  }, [customerId]);
  
  const fetchStatus = async () => {
    setIsLoading(true);
    try {
      const res = await getAgenticAuthorizationStatus(customerId);
      if (res && res.status !== "none") {
        setStatus(res);
        onStatusChange?.("ACTIVE");
      } else {
        setStatus(null);
        onStatusChange?.("NONE");
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleSetup = async () => {
    setIsLoading(true);
    try {
      const res = await setupAgenticAuthorization(customerId, perTxLimit, dailyLimit);
      setStatus(res);
      setIsConfiguring(false);
      onStatusChange?.("ACTIVE");
    } catch (e) {
      alert("Failed to setup agentic authorization");
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleRevoke = async () => {
    if (!confirm("Are you sure you want to revoke Agentic Payment capabilities?")) return;
    setIsLoading(true);
    try {
      await revokeAgenticAuthorization(customerId);
      setStatus(null);
      onStatusChange?.("NONE");
    } catch (e) {
      alert("Failed to revoke authorization");
    } finally {
      setIsLoading(false);
    }
  };
  
  if (!customerId) return null;
  
  return (
    <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border border-indigo-100 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            ✨ Agentic Payments
            {status && <span className="bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full uppercase tracking-wider font-bold">Active</span>}
          </h3>
          <p className="text-sm text-gray-600">Enable AI-driven autonomous checkout with predefined guardrails.</p>
        </div>
      </div>
      
      {isLoading ? (
        <div className="animate-pulse flex space-x-4">
          <div className="flex-1 space-y-4 py-1">
            <div className="h-4 bg-indigo-200 rounded w-3/4"></div>
            <div className="space-y-2">
              <div className="h-4 bg-indigo-200 rounded"></div>
            </div>
          </div>
        </div>
      ) : status ? (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 text-sm">
             <div className="flex justify-between items-center py-2 border-b border-gray-50">
               <span className="text-gray-600">Payment Rail</span>
               <span className="font-semibold text-gray-900">{status.rail}</span>
             </div>
             <div className="flex justify-between items-center py-2 border-b border-gray-50">
               <span className="text-gray-600">Per-Transaction Limit</span>
               <span className="font-semibold text-gray-900">₹{status.per_transaction_limit}</span>
             </div>
             <div className="flex justify-between items-center py-2 border-b border-gray-50">
               <span className="text-gray-600">Daily Limit</span>
               <span className="font-semibold text-gray-900">₹{status.daily_limit}</span>
             </div>
             <div className="flex justify-between items-center py-2">
               <span className="text-gray-600">Spent Today</span>
               <span className="font-semibold text-gray-900">₹{status.spent_today}</span>
             </div>
          </div>
          
          <button 
            onClick={handleRevoke}
            className="w-full py-2 px-4 bg-white border border-red-200 text-red-600 rounded-lg hover:bg-red-50 text-sm font-medium transition-colors"
          >
            Revoke Access
          </button>
        </div>
      ) : isConfiguring ? (
        <div className="space-y-4 bg-white p-4 rounded-lg shadow-sm border border-indigo-100">
           <div>
             <label className="block text-sm font-medium text-gray-700 mb-1">Per-Transaction Limit (₹)</label>
             <input type="number" value={perTxLimit} onChange={e => setPerTxLimit(Number(e.target.value))} className="w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 border" />
           </div>
           <div>
             <label className="block text-sm font-medium text-gray-700 mb-1">Daily Limit (₹)</label>
             <input type="number" value={dailyLimit} onChange={e => setDailyLimit(Number(e.target.value))} className="w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 border" />
           </div>
           
           <div className="flex gap-2 pt-2">
             <button onClick={() => setIsConfiguring(false)} className="flex-1 py-2 px-4 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50">Cancel</button>
             <button onClick={handleSetup} className="flex-1 py-2 px-4 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">Enable Agentic Pay</button>
           </div>
        </div>
      ) : (
        <button 
          onClick={() => setIsConfiguring(true)}
          className="w-full py-2.5 px-4 bg-indigo-600 text-white rounded-lg text-sm font-bold hover:bg-indigo-700 shadow-sm transition-colors flex justify-center items-center gap-2"
        >
          Setup Agentic Payments
        </button>
      )}
    </div>
  )
}

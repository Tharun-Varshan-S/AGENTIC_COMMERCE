"use client";

import { useEffect, useState } from "react";
import { fetchPaymentHistory, fetchOrderAuditLogs, fetchPaymentAuditLogs } from "@/lib/api";

import { CheckCircle2, XCircle, Clock, FileText, ExternalLink, ChevronDown, ChevronUp, ShieldX } from "lucide-react";

type PaymentHistoryItem = {
  id: string;
  local_order_id: string;
  razorpay_order_id: string | null;
  razorpay_payment_id: string | null;
  amount: number;
  currency: string;
  status: string;
  webhook_verified: boolean;
  created_at: string;
};

type BlockedEvent = {
  id: string;
  action: string;
  created_at: string;
  metadata: Record<string, any>;
};

export default function PaymentHistoryPage() {
  const [payments, setPayments] = useState<PaymentHistoryItem[]>([]);
  const [blockedEvents, setBlockedEvents] = useState<BlockedEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedOrderId, setExpandedOrderId] = useState<string | null>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [loadingAudit, setLoadingAudit] = useState(false);

  const toggleExpand = async (orderId: string, localOrderId: string) => {
    if (expandedOrderId === orderId) {
      setExpandedOrderId(null);
      return;
    }
    setExpandedOrderId(orderId);
    setLoadingAudit(true);
    setAuditLogs([]);
    try {
      // The API now accepts both UUID and order_number (human-readable)
      const logs = await fetchOrderAuditLogs(localOrderId);
      setAuditLogs(logs);
    } catch (e) {
      console.error("Failed to load audit logs", e);
    } finally {
      setLoadingAudit(false);
    }
  };

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchPaymentHistory();
        setPayments(data.payments);

        // GAP-12: Also load GATE_FAILED events from audit trail
        // These are blocked purchases that never created a payment record
        // We pull them from the merchant-level audit log
        try {
          // Use the first merchant if available — the API will scope to current user
          const auditData = await fetch(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api"}/payments/audit`,
            {
              headers: {
                Authorization: `Bearer ${localStorage.getItem("agentic_auth_token") || ""}`,
              },
            }
          );
          if (auditData.ok) {
            const allLogs: any[] = await auditData.json();
            const gateFailures = allLogs.filter((log: any) =>
              log.action?.startsWith("GATE_FAILED:") ||
              log.action?.startsWith("RAZORPAY_PROVIDER_ERROR")
            );
            setBlockedEvents(gateFailures);
          }
        } catch (e) {
          // Non-critical: blocked events are bonus info
          console.warn("Could not load blocked events", e);
        }
      } catch (e) {
        console.error("Failed to load history", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const getStatusIcon = (status: string) => {
    if (status === "PAID" || status === "CAPTURED") {
      return <CheckCircle2 className="w-5 h-5 text-green-500" />;
    }
    if (status === "FAILED") {
      return <XCircle className="w-5 h-5 text-red-500" />;
    }
    if (status === "BLOCKED") {
      return <ShieldX className="w-5 h-5 text-orange-500" />;
    }
    return <Clock className="w-5 h-5 text-yellow-500" />;
  };

  const getStatusColor = (status: string) => {
    if (status === "PAID" || status === "CAPTURED") return "bg-green-100 text-green-800";
    if (status === "FAILED") return "bg-red-100 text-red-800";
    if (status === "BLOCKED") return "bg-orange-100 text-orange-800";
    return "bg-yellow-100 text-yellow-800";
  };

  const getBlockedReason = (action: string) => {
    if (action.includes("TransactionLimitExceeded")) return "Amount exceeded per-transaction limit";
    if (action.includes("DailyLimitExceeded")) return "Daily spending limit reached";
    if (action.includes("SpendingLimitNotConfigured")) return "No spending limit configured";
    if (action.includes("InsufficientInventory")) return "Insufficient inventory";
    if (action.includes("MerchantInactive")) return "Merchant inactive";
    if (action.includes("RAZORPAY_PROVIDER_ERROR")) return "Payment provider error";
    return action.replace("GATE_FAILED:", "").replace(/_/g, " ");
  };

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Loading payment history...</div>;
  }

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      <div className="flex items-center space-x-3 pb-6 border-b">
        <FileText className="w-8 h-8 text-indigo-600" />
        <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Payment History</h1>
      </div>

      {/* GAP-12: Blocked purchases section */}
      {blockedEvents.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-orange-700 flex items-center gap-2">
            <ShieldX className="w-5 h-5" />
            Blocked Purchases ({blockedEvents.length})
          </h2>
          <div className="grid gap-3">
            {blockedEvents.map((event) => (
              <div key={event.id} className="bg-orange-50 border border-orange-200 rounded-lg p-4 flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <ShieldX className="w-4 h-4 text-orange-600 shrink-0" />
                    <span className="font-semibold text-orange-900 text-sm">
                      Blocked — {getBlockedReason(event.action)}
                    </span>
                  </div>
                  {event.metadata?.reason && (
                    <p className="text-xs text-orange-700 ml-6">{event.metadata.reason}</p>
                  )}
                  {event.metadata?.amount && (
                    <p className="text-xs text-orange-600 ml-6">
                      Attempted amount: ₹{Number(event.metadata.amount).toFixed(2)}
                    </p>
                  )}
                </div>
                <span className="text-xs text-orange-500 shrink-0 ml-4">
                  {new Date(event.created_at).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {payments.length === 0 && blockedEvents.length === 0 ? (
        <div className="text-center p-12 bg-gray-50 rounded-lg border border-gray-100">
          <p className="text-gray-500 text-lg">No payment history found.</p>
        </div>
      ) : payments.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-700">Payment Records ({payments.length})</h2>
          <div className="grid gap-6">
            {payments.map((payment) => (
              <div key={payment.id} className="bg-white rounded-lg border shadow-sm overflow-hidden hover:shadow-md transition-shadow">
                <div className="bg-gray-50 border-b p-6 flex flex-row items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(payment.status)}
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900 m-0">
                        Order {payment.local_order_id}
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">
                        {new Date(payment.created_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-bold text-gray-900">
                      ₹{(payment.amount).toFixed(2)}
                    </div>
                    <span className={`mt-1 inline-block border rounded-full font-medium px-2.5 py-0.5 text-xs ${getStatusColor(payment.status)}`}>
                      {payment.status}
                    </span>
                  </div>
                </div>
                <div className="p-6 pt-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div className="space-y-3">
                      <div className="flex flex-col space-y-1">
                        <span className="text-gray-500 font-medium">Razorpay Order ID</span>
                        <span className="font-mono text-gray-900 bg-gray-100 px-2 py-1 rounded inline-block w-fit">
                          {payment.razorpay_order_id || "N/A"}
                        </span>
                      </div>
                      <div className="flex flex-col space-y-1">
                        <span className="text-gray-500 font-medium">Razorpay Payment ID</span>
                        <span className="font-mono text-gray-900 bg-gray-100 px-2 py-1 rounded inline-block w-fit">
                          {payment.razorpay_payment_id || "N/A"}
                        </span>
                      </div>
                    </div>
                    
                    <div className="space-y-3">
                      <div className="flex flex-col space-y-1">
                        <span className="text-gray-500 font-medium">Webhook Verified</span>
                        <div className="flex items-center space-x-2">
                          <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-semibold ${payment.webhook_verified ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                            {payment.webhook_verified ? "Yes (Genuine)" : "No / Pending"}
                          </span>
                          {payment.webhook_verified && (
                            <CheckCircle2 className="w-4 h-4 text-green-600" />
                          )}
                        </div>
                      </div>
                      {/* Receipt link for captured payments */}
                      {(payment.status === "PAID" || payment.status === "CAPTURED") && (
                        <div className="flex flex-col space-y-1">
                          <span className="text-gray-500 font-medium">Receipt</span>
                          <a
                            href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080/api"}/payments/receipt/${payment.id}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center space-x-1 text-indigo-600 hover:text-indigo-800 text-xs font-medium transition-colors"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                            <span>View Receipt</span>
                          </a>
                        </div>
                      )}
                    </div>

                  </div>
                </div>

                <div className="bg-gray-50 border-t px-6 py-3 cursor-pointer flex justify-between items-center text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors" onClick={() => toggleExpand(payment.id, payment.local_order_id)}>
                  <span>Audit Trail</span>
                  {expandedOrderId === payment.id ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </div>

                {expandedOrderId === payment.id && (
                  <div className="border-t p-6 bg-gray-50">
                    {loadingAudit ? (
                      <div className="text-gray-500 text-sm">Loading audit trail...</div>
                    ) : auditLogs.length === 0 ? (
                      <div className="text-gray-500 text-sm">No audit logs found for this order.</div>
                    ) : (
                      <div className="space-y-3">
                        {auditLogs.map((log) => (
                          <div key={log.id} className="flex flex-col bg-white p-4 rounded border text-sm">
                            <div className="flex justify-between items-start mb-2">
                              <span className="font-semibold text-gray-900">{log.action}</span>
                              <span className="text-xs text-gray-500">{new Date(log.created_at).toLocaleString()}</span>
                            </div>
                            <div className="flex space-x-2 text-xs text-gray-600 mb-2">
                              <span className="bg-gray-100 px-2 py-1 rounded">Actor: {log.actor_type}</span>
                              <span className="bg-gray-100 px-2 py-1 rounded">Type: {log.event_type}</span>
                            </div>
                            <div className="text-xs font-mono text-gray-500 bg-gray-50 p-2 rounded whitespace-pre-wrap overflow-auto">
                              {JSON.stringify(log.metadata, null, 2)}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  UserCircle, Shield, CreditCard, ArrowLeft, Save,
  CheckCircle, AlertTriangle, Loader2, Trash2, ExternalLink
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import {
  API_BASE,
  fetchCustomerSettings, updateCustomerSettings,
  setupInstrument, saveInstrumentToken, revokeInstrumentToken
} from "@/lib/api";

declare global {
  interface Window { Razorpay: any; }
}

const MERCHANT_ID = process.env.NEXT_PUBLIC_MERCHANT_ID || "";

export default function ProfilePage() {
  const router = useRouter();
  const { user } = useAuth();

  // Settings state
  const [txLimit, setTxLimit] = useState<number>(5000);
  const [dailyLimit, setDailyLimit] = useState<number>(50000);
  const [limitSet, setLimitSet] = useState(false);
  const [savingLimits, setSavingLimits] = useState(false);
  const [limitSaved, setLimitSaved] = useState(false);
  const [limitError, setLimitError] = useState<string | null>(null);

  // Instrument state
  const [hasSavedToken, setHasSavedToken] = useState(false);
  const [tokenSuffix, setTokenSuffix] = useState<string | null>(null);
  const [instrumentLoading, setInstrumentLoading] = useState(false);
  const [instrumentMsg, setInstrumentMsg] = useState<string | null>(null);
  const [instrumentError, setInstrumentError] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);

  // Load settings + instrument status
  const load = useCallback(async () => {
    if (!MERCHANT_ID) { setLoading(false); return; }
    try {
      const [settings, instrument] = await Promise.all([
        fetchCustomerSettings(MERCHANT_ID),
        setupInstrument(MERCHANT_ID).catch(() => null)
      ]);
      setTxLimit(settings.transaction_limit);
      setDailyLimit(settings.daily_limit);
      setLimitSet(settings.spending_limit_set);
      if (instrument) {
        setHasSavedToken(instrument.has_saved_token);
        setTokenSuffix(instrument.token_suffix);
      }
    } catch (e) {
      // ignore load errors silently — user sees defaults
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Load Razorpay script once
  useEffect(() => {
    if (typeof window !== "undefined" && !window.Razorpay) {
      const script = document.createElement("script");
      script.src = "https://checkout.razorpay.com/v1/checkout.js";
      document.head.appendChild(script);
    }
  }, []);

  async function handleSaveLimits() {
    setSavingLimits(true);
    setLimitError(null);
    setLimitSaved(false);
    try {
      await updateCustomerSettings(MERCHANT_ID, txLimit, dailyLimit);
      setLimitSet(true);
      setLimitSaved(true);
      setTimeout(() => setLimitSaved(false), 3000);
    } catch (e: any) {
      setLimitError(e.message || "Failed to save limits");
    } finally {
      setSavingLimits(false);
    }
  }

  async function handleAuthorizeInstrument() {
    setInstrumentLoading(true);
    setInstrumentError(null);
    setInstrumentMsg(null);
    try {
      const setup = await setupInstrument(MERCHANT_ID);

      if (setup.has_saved_token) {
        setHasSavedToken(true);
        setTokenSuffix(setup.token_suffix);
        setInstrumentMsg("Payment method already authorized.");
        setInstrumentLoading(false);
        return;
      }

      // Open Razorpay Checkout in SAVE mode — user enters test card ONCE
      const rzp = new window.Razorpay({
        key: setup.razorpay_key_id,
        name: "TechNova AI Commerce",
        description: "Authorize your agent to pay on your behalf",
        // Amount 0 — we're only saving the card, not charging
        // Razorpay requires a small non-zero amount for tokenization on some accounts
        amount: 100, // ₹1 — refundable test charge
        currency: "INR",
        customer_id: setup.razorpay_customer_id,
        recurring: 1,
        callback_url: "", // S2S — handled below in handler
        prefill: {
          email: user?.email || "",
          contact: "9999999999",
          // Pre-fill test card for demo convenience — CLEARLY LABELLED AS TEST DATA
          "method.card.number": "4111111111111111",
          "method.card.expiry": "12/28",
          "method.card.cvv": "123",
          name: user?.full_name || user?.email?.split("@")[0] || "Agent User"
        },
        notes: {
          instrument_mode: "one_time_setup",
          purpose: "agentic_commerce_authorization"
        },
        theme: { color: "#4f46e5" },
        modal: {
          ondismiss: () => {
            setInstrumentLoading(false);
            setInstrumentMsg("Setup cancelled. You can authorize later from Profile.");
          }
        },
        handler: async (response: any) => {
          // Checkout returned — save the token
          try {
            const tokenId =
              response.razorpay_subscription_id ||    // subscription flow
              response.razorpay_payment_id ||          // fallback: use payment_id as reference
              "manual_token";

            // Try to get the token from the payment's token list
            // (Razorpay returns token in response when save=1)
            const actualToken = response.razorpay_token || response.razorpay_payment_id;

            await saveInstrumentToken(actualToken, setup.razorpay_customer_id, MERCHANT_ID);
            setHasSavedToken(true);
            setTokenSuffix(actualToken.slice(-6));
            setInstrumentMsg("✅ Payment method authorized! Your agent can now pay without card entry.");
          } catch (e: any) {
            setInstrumentError("Payment completed but token save failed: " + e.message);
          } finally {
            setInstrumentLoading(false);
          }
        }
      });
      rzp.open();
    } catch (e: any) {
      setInstrumentError(e.message || "Failed to start setup");
      setInstrumentLoading(false);
    }
  }

  async function handleRevoke() {
    if (!confirm("Remove saved payment method? Your agent will need Checkout.js for the next purchase.")) return;
    setInstrumentLoading(true);
    try {
      await revokeInstrumentToken();
      setHasSavedToken(false);
      setTokenSuffix(null);
      setInstrumentMsg("Payment method removed.");
    } catch (e: any) {
      setInstrumentError(e.message);
    } finally {
      setInstrumentLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-600" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center space-x-3">
          <Link href="/buyer" className="p-2 text-gray-500 hover:text-indigo-600 transition-colors rounded-lg hover:bg-gray-100">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Profile & Settings</h1>
            <p className="text-xs text-gray-500">Manage your agent spending limits and payment authorization</p>
          </div>
        </div>
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <UserCircle className="w-5 h-5 text-indigo-500" />
          <span className="font-medium">{user?.full_name || user?.email}</span>
        </div>
      </div>

      <div className="max-w-2xl mx-auto py-8 px-4 space-y-6">

        {/* Identity Card */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          <div className="bg-gradient-to-r from-indigo-600 to-violet-600 px-6 py-5">
            <div className="flex items-center space-x-4">
              <div className="w-14 h-14 rounded-full bg-white/20 flex items-center justify-center">
                <UserCircle className="w-8 h-8 text-white" />
              </div>
              <div>
                <p className="text-white font-semibold text-lg">{user?.full_name || "Agent User"}</p>
                <p className="text-indigo-200 text-sm">{user?.email}</p>
                <span className="inline-block mt-1 bg-white/20 text-white text-xs px-2 py-0.5 rounded-full">
                  {user?.role || "CUSTOMER"}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Spending Limits */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm">
          <div className="px-6 py-5 border-b border-gray-100 flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center">
              <Shield className="w-5 h-5 text-indigo-600" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">Agent Spending Limits</h2>
              <p className="text-xs text-gray-500">Server-enforced — agent cannot exceed these limits per purchase</p>
            </div>
            {limitSet && (
              <span className="ml-auto inline-flex items-center space-x-1 text-xs text-emerald-700 bg-emerald-50 px-2 py-1 rounded-full">
                <CheckCircle className="w-3 h-3" />
                <span>Active</span>
              </span>
            )}
          </div>
          <div className="px-6 py-5 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Per-Transaction Limit (₹)
              </label>
              <input
                type="number"
                min={1}
                max={100000}
                value={txLimit}
                onChange={e => setTxLimit(Number(e.target.value))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="e.g. 5000"
              />
              <p className="text-xs text-gray-400 mt-1">Agent will be blocked if a single purchase exceeds this</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Daily Limit (₹)
              </label>
              <input
                type="number"
                min={1}
                max={500000}
                value={dailyLimit}
                onChange={e => setDailyLimit(Number(e.target.value))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                placeholder="e.g. 50000"
              />
              <p className="text-xs text-gray-400 mt-1">Total spending across all agent transactions today</p>
            </div>

            {limitError && (
              <div className="flex items-center space-x-2 text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                <span>{limitError}</span>
              </div>
            )}
            {limitSaved && (
              <div className="flex items-center space-x-2 text-emerald-700 text-sm bg-emerald-50 px-3 py-2 rounded-lg">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                <span>Limits saved successfully</span>
              </div>
            )}

            <button
              onClick={handleSaveLimits}
              disabled={savingLimits}
              className="w-full flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm"
            >
              {savingLimits ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              <span>{savingLimits ? "Saving…" : "Save Limits"}</span>
            </button>
          </div>
        </div>

        {/* Saved Payment Instrument */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm">
          <div className="px-6 py-5 border-b border-gray-100 flex items-center space-x-3">
            <div className="w-9 h-9 rounded-lg bg-violet-50 flex items-center justify-center">
              <CreditCard className="w-5 h-5 text-violet-600" />
            </div>
            <div>
              <h2 className="font-semibold text-gray-900">Agent Payment Authorization</h2>
              <p className="text-xs text-gray-500">One-time setup — your agent uses this for headless purchases</p>
            </div>
            {hasSavedToken && (
              <span className="ml-auto inline-flex items-center space-x-1 text-xs text-emerald-700 bg-emerald-50 px-2 py-1 rounded-full">
                <CheckCircle className="w-3 h-3" />
                <span>Authorized</span>
              </span>
            )}
          </div>
          <div className="px-6 py-5 space-y-4">
            {hasSavedToken ? (
              <>
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start space-x-3">
                  <CheckCircle className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-emerald-800 text-sm">Payment method authorized</p>
                    <p className="text-emerald-700 text-xs mt-1">
                      Saved instrument ···{tokenSuffix} is active. Your agent will charge this directly — no card entry needed per purchase.
                    </p>
                  </div>
                </div>
                <div className="flex space-x-3">
                  <button
                    onClick={handleAuthorizeInstrument}
                    disabled={instrumentLoading}
                    className="flex-1 flex items-center justify-center space-x-2 border border-indigo-300 text-indigo-700 hover:bg-indigo-50 font-medium py-2.5 px-4 rounded-lg transition-colors text-sm disabled:opacity-60"
                  >
                    {instrumentLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                    <span>Re-authorize</span>
                  </button>
                  <button
                    onClick={handleRevoke}
                    disabled={instrumentLoading}
                    className="flex items-center justify-center space-x-2 border border-red-200 text-red-600 hover:bg-red-50 font-medium py-2.5 px-4 rounded-lg transition-colors text-sm disabled:opacity-60"
                  >
                    <Trash2 className="w-4 h-4" />
                    <span>Remove</span>
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start space-x-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-amber-800 text-sm">No payment method saved</p>
                    <p className="text-amber-700 text-xs mt-1">
                      Without authorization, your agent falls back to Razorpay Checkout (you must enter card details each time). Authorize once to enable fully headless purchases.
                    </p>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-xl p-4 text-xs text-gray-600 space-y-1 border border-gray-100">
                  <p className="font-semibold text-gray-700 mb-2">How it works</p>
                  <p>1. Click "Authorize Agent to Pay" — Razorpay Checkout opens</p>
                  <p>2. Enter the <strong>test card</strong>: 4111 1111 1111 1111, expiry 12/28, CVV 123</p>
                  <p>3. Your token is saved securely — this is the ONLY time you enter card details</p>
                  <p>4. Every future agent purchase is headless (no card entry, no Checkout popup)</p>
                </div>

                <button
                  onClick={handleAuthorizeInstrument}
                  disabled={instrumentLoading}
                  className="w-full flex items-center justify-center space-x-2 bg-violet-600 hover:bg-violet-700 disabled:opacity-60 text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm"
                >
                  {instrumentLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                  <span>{instrumentLoading ? "Opening Razorpay…" : "Authorize Agent to Pay"}</span>
                </button>
              </>
            )}

            {instrumentMsg && (
              <div className="flex items-center space-x-2 text-emerald-700 text-sm bg-emerald-50 px-3 py-2 rounded-lg">
                <CheckCircle className="w-4 h-4 flex-shrink-0" />
                <span>{instrumentMsg}</span>
              </div>
            )}
            {instrumentError && (
              <div className="flex items-start space-x-2 text-red-600 text-sm bg-red-50 px-3 py-2 rounded-lg">
                <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>{instrumentError}</span>
              </div>
            )}
          </div>
        </div>

        {/* Quick links */}
        <div className="flex space-x-3">
          <Link
            href="/buyer/history"
            className="flex-1 flex items-center justify-center space-x-2 bg-white border border-gray-200 rounded-xl py-3 text-sm text-gray-700 hover:border-indigo-300 hover:text-indigo-700 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            <span>Payment History</span>
          </Link>
          <Link
            href="/buyer"
            className="flex-1 flex items-center justify-center space-x-2 bg-indigo-600 rounded-xl py-3 text-sm text-white hover:bg-indigo-700 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Shop</span>
          </Link>
        </div>
      </div>
    </div>
  );
}

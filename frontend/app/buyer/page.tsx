"use client";

declare global {
  interface Window {
    Razorpay: any;
  }
}

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  fetchProducts, 
  fetchActiveCart, 
  createCart, 
  addCartItem, 
  updateCartItem, 
  removeCartItem,
  fetchMerchants,
  executeTool,
  evaluatePolicy,
  requestConsent,
  approveConsent,
  declineConsent,
  chatWithAgent,
  createPaymentOrder,
  createDirectPaymentOrder,
  verifyPayment,
  respondToUpsell,
  fetchCustomerSettings,
  updateCustomerSettings,
  executePurchase
} from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { BuyerHeader } from "@/components/buyer/buyer-header";
import { AiChat, Message } from "@/components/buyer/ai-chat";
import { ProductResults } from "@/components/buyer/product-results";
import { ProductDetails } from "@/components/buyer/product-details";
import { CartDrawer } from "@/components/buyer/cart-drawer";
import { RecommendationCard } from "@/components/buyer/recommendation-card";

import { AgentOrchestration, OrchestrationEvent } from "@/components/buyer/agent-orchestration";

// Initialize
export default function BuyerPage() {
  const [merchantId, setMerchantId] = useState<string>("");
  const [cart, setCart] = useState<any>(null);
  const [sessionId] = useState<string>(() => Date.now().toString());
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [orchestrationEvents, setOrchestrationEvents] = useState<OrchestrationEvent[]>([]);
  
  const [products, setProducts] = useState<any[]>([]);
  const [isProductsLoading, setIsProductsLoading] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  
  const [recommendation, setRecommendation] = useState<any>(null);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isCartLoading, setIsCartLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [upsellSuggestions, setUpsellSuggestions] = useState<any[]>([]);
  
  // Policy & Consent State
  const [policyDecision, setPolicyDecision] = useState<any>(null);
  const [consentRequest, setConsentRequest] = useState<any>(null);
  const [isConsentModalOpen, setIsConsentModalOpen] = useState(false);
  const [isProcessingConsent, setIsProcessingConsent] = useState(false);
  
  // Agentic Payment processing state
  const [approvalState, setApprovalState] = useState<'IDLE' | 'WAITING_FOR_HUMAN_APPROVAL' | 'AGENT_PAYMENT_AUTHORIZED' | 'AGENT_EXECUTING_PURCHASE' | 'RAZORPAY_PAYMENT_PROCESSING' | 'VERIFYING' | 'SUCCESS' | 'PURCHASE_FAILED'>('IDLE');
  const [pendingPurchase, setPendingPurchase] = useState<any>(null);
  const [purchaseSteps, setPurchaseSteps] = useState<Array<{
    step: string;
    status: 'running' | 'passed' | 'blocked';
    detail: string;
    metadata?: Record<string, any>;
  }>>([]);
  
  // Settings
  const [customerSettings, setCustomerSettings] = useState<{
    transaction_limit: number;
    daily_limit: number;
    spending_limit_set: boolean;
  } | null>(null);
  
  const { user, isLoading } = useAuth();
  const router = useRouter();


  // Initialize
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [merchants] = await Promise.all([
          fetchMerchants()
        ]);
        if (merchants && merchants.length > 0) {
          setMerchantId(merchants[0].id);
        }
      } catch (err) {
        setError("Unable to connect to the commerce service. Please try again.");
      }
    }
    loadInitialData();
  }, []);

  // Load cart and recommendations when merchant changes
  useEffect(() => {
    if (!merchantId) return;
    
    async function loadCustomerData() {
      try {
        let activeCart = await fetchActiveCart(merchantId);
        if (!activeCart && merchantId) {
          activeCart = await createCart(merchantId);
        }
        setCart(activeCart);
        setRecommendation(null);
        if (activeCart && activeCart.items && activeCart.items.length > 0) {
            checkPolicy(merchantId, activeCart.id);
        } else {
            setPolicyDecision(null);
        }
        
        const settings = await fetchCustomerSettings(merchantId);
        setCustomerSettings(settings);
      } catch (err) {
        console.error(err);
      }
    }
    loadCustomerData();
  }, [merchantId]);

  const checkPolicy = async (mId: string, cartId: string) => {
    try {
      const decision = await evaluatePolicy(mId, cartId);
      setPolicyDecision(decision);
    } catch (err) {
      console.error("Failed to evaluate policy", err);
    }
  };

  const reloadCart = async () => {
    if (!merchantId) return;
    try {
      const activeCart = await fetchActiveCart(merchantId);
      setCart(activeCart);
      if (activeCart && activeCart.items && activeCart.items.length > 0) {
        checkPolicy(merchantId, activeCart.id);
      } else {
        setPolicyDecision(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleSendMessage = async (text: string, approved?: boolean) => {
    const newMessage: Message = { id: Date.now().toString(), sender: "USER", text };
    setMessages(prev => [...prev, newMessage]);
    setIsChatLoading(true);
    setIsProductsLoading(true);
    setError(null);
    setOrchestrationEvents([]);
    setUpsellSuggestions([]);

    try {
      const response = await chatWithAgent(
        sessionId, 
        merchantId, 
        text,
        (event) => {
          setOrchestrationEvents(prev => [...prev, event]);
        },
        approved
      );
      
      // Update UI state from structured agent response
      if (response.products) {
        setProducts(response.products);
      }
      
      if (response.recommendation) {
        setRecommendation(response.recommendation);
      } else if (response.products && response.products.length === 0) {
        setRecommendation(null);
      }
      
      if (response.cart) {
        setCart(response.cart);
      }
      
      if (response.policy) {
        setPolicyDecision(response.policy);
      }
      if (response.checkout_session) {
        if (response.checkout_session.razorpay_order_id) {
            setApprovalState('RAZORPAY_PAYMENT_PROCESSING');
            handleRazorpayCheckout(response.checkout_session);
        } else if (response.checkout_session.checkout_ready) {
            setApprovalState('IDLE');
            setPendingPurchase(null);
            await reloadCart();
            setIsCartOpen(true);
        }
      } else {
          setApprovalState('IDLE');
          setPendingPurchase(null);
      }
      
      if (response.upsell_suggestions && response.upsell_suggestions.length > 0) {
        setUpsellSuggestions(response.upsell_suggestions);
      }
      
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: "AI ASSISTANT",
        text: response.message,
        toolCalls: response.tool_calls
      }]);

    } catch (err: any) {
      console.error("Agent communication error:", err);
      
      let errorMessage = "I'm having trouble connecting to the AI assistant right now. Please try again.";
      
      if (err.name === 'APIError' || typeof err.status === 'number') {
        if (err.status === 404) {
          errorMessage = "Connection issue: Unable to reach the AI assistant.";
        } else if (err.status === 401 || err.status === 403) {
          errorMessage = "Please sign in to chat with the AI assistant.";
        } else if (err.status === 429) {
          errorMessage = err.message || "I'm receiving too many requests right now. Please wait a moment and try again.";
        } else if (err.status !== 500 && err.message) {
          errorMessage = err.message;
        }
      } else if (err.message && err.message.includes('NetworkError')) {
        errorMessage = "Connection issue: Unable to reach the AI assistant.";
      }

      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: "AI ASSISTANT",
        text: errorMessage
      }]);
      setApprovalState('IDLE');
      setPendingPurchase(null);
    } finally {
      setIsChatLoading(false);
      setIsProductsLoading(false);
    }
  };

  const handleAddToCart = async (product: any) => {
    if (!cart) {
      alert("Cart not ready.");
      return;
    }
    try {
      await addCartItem(cart.id, product.id, 1, product.offer_id);
      await reloadCart();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleBuyNow = async (product: any) => {
    if (!merchantId) {
      alert("Merchant not ready.");
      return;
    }
    // Gate on spending limit — redirect to profile page if not set
    if (!customerSettings || !customerSettings.spending_limit_set) {
      router.push('/buyer/profile');
      return;
    }
    // Prevent re-entry if already in-flight
    if (approvalState !== 'IDLE') return;
    setPendingPurchase({ type: 'buy_now', product });
    setApprovalState('WAITING_FOR_HUMAN_APPROVAL');
  };

  const handleUpdateCartItem = async (itemId: string, quantity: number) => {
    if (!cart) return;
    try {
      await updateCartItem(cart.id, itemId, quantity);
      await reloadCart();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleRemoveCartItem = async (itemId: string) => {
    if (!cart) return;
    try {
      await removeCartItem(cart.id, itemId);
      await reloadCart();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleUpsellResponse = async (offerId: string, action: 'accept' | 'decline') => {
    if (!merchantId || !cart) return;
    try {
      await respondToUpsell(merchantId, cart.id, offerId, action);
      
      // Remove from suggestions array
      setUpsellSuggestions(prev => prev.filter(s => s.id !== offerId));
      
      if (action === 'accept') {
        await reloadCart();
      }
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleInitiatePurchase = async () => {
    if (!cart) return;
    // Gate on spending limit
    if (!customerSettings || !customerSettings.spending_limit_set) {
      router.push('/buyer/profile');
      return;
    }
    if (approvalState !== 'IDLE') return;
    setPendingPurchase({ type: 'cart' });
    setApprovalState('WAITING_FOR_HUMAN_APPROVAL');
  };

  const handleApprovePurchase = async () => {
    setApprovalState('AGENT_EXECUTING_PURCHASE');
    setPurchaseSteps([]);
    
    try {
      let res;
      if (pendingPurchase.type === 'buy_now') {
        res = await executePurchase(merchantId!, "buy_now", {
          product_id: pendingPurchase.product.id,
          offer_id: pendingPurchase.product.offer_id,
          quantity: 1
        }, (step) => {
          setPurchaseSteps(prev => {
            const existing = prev.findIndex(s => s.step === step.step);
            if (existing >= 0) {
              const updated = [...prev];
              updated[existing] = step;
              return updated;
            }
            return [...prev, step];
          });
        });
      } else {
        res = await executePurchase(merchantId!, "cart", {
          cart_id: cart?.id
        }, (step) => {
          setPurchaseSteps(prev => {
            const existing = prev.findIndex(s => s.step === step.step);
            if (existing >= 0) {
              const updated = [...prev];
              updated[existing] = step;
              return updated;
            }
            return [...prev, step];
          });
        });
      }
      
      // HEADLESS PATH: if the agent already captured the payment S2S, skip Checkout.js entirely
      if (res.payment_mode === 'headless_s2s') {
        setApprovalState('SUCCESS');
        setPendingPurchase((prev: any) => ({
          ...prev,
          finalPaymentId: res.razorpay_payment_id,
          finalAmount: res.amount_rupees,
          finalTimestamp: res.captured_at || new Date().toISOString(),
          receiptUrl: res.receipt_url
        }));
        setMessages(prev => [...prev, {
          id: Date.now().toString(),
          sender: "AI ASSISTANT",
          text: `✅ Payment captured headlessly! Payment ID: ${res.razorpay_payment_id} — no card entry required.`
        }]);
        await reloadCart();
        setTimeout(() => {
          setApprovalState('IDLE');
          setPendingPurchase(null);
          setPurchaseSteps([]);
          setIsCartOpen(false);
        }, 6000);
        return;
      }

      // FALLBACK PATH: open Razorpay Checkout.js modal
      setApprovalState('RAZORPAY_PAYMENT_PROCESSING');
      handleRazorpayCheckout(res);
      
    } catch (err: any) {
      console.error("Purchase execution failed:", err);
      const errorClass = (err as any).error_class;
      let userMessage = err.message || "An error occurred while executing the purchase.";
      if (errorClass === 'SpendingLimitNotConfigured') {
        userMessage = "No spending limit set. Please configure a limit in your Profile before making purchases.";
      } else if (errorClass === 'TransactionLimitExceeded') {
        userMessage = `Blocked: ${err.message}`;
      } else if (errorClass === 'DailyLimitExceeded') {
        userMessage = `Blocked: ${err.message}`;
      } else if (errorClass === 'RazorpayProviderError') {
        userMessage = `Payment provider unavailable: ${err.message}`;
      } else if (errorClass === 'SavedInstrumentInvalid') {
        userMessage = `Saved payment method invalid. Go to Profile → Authorize Agent to Pay.`;
      } else if (errorClass === 'ChargeDeclined') {
        userMessage = `Charge declined by card issuer. No retry attempted. ${err.message}`;
      }
      setError(userMessage);
      setApprovalState('PURCHASE_FAILED');
    }
  };
  
  const handleCancelPurchase = () => {
    setApprovalState('IDLE');
    setPendingPurchase(null);
    setError(null);
  };

  const handleRazorpayCheckout = (paymentOrder: any) => {
    if (!window.Razorpay) {
      setError("Razorpay SDK failed to load. Are you offline?");
      setApprovalState('IDLE');
      setPendingPurchase(null);
      return;
    }

    const options = {
      key: paymentOrder.razorpay_key_id,
      amount: paymentOrder.amount,
      currency: paymentOrder.currency,
      name: "AI-Native Commerce",
      description: "Purchase Order",
      order_id: paymentOrder.razorpay_order_id,
      handler: async function (response: any) {
        try {
          setApprovalState('VERIFYING');
          const verifyRes = await verifyPayment(
            paymentOrder.payment_id,
            response.razorpay_payment_id,
            response.razorpay_order_id,
            response.razorpay_signature
          );
          
          if (verifyRes.status === "success") {
            setApprovalState('SUCCESS');
            setPendingPurchase((prev: any) => ({
              ...prev,
              finalPaymentId: response.razorpay_payment_id,
              finalAmount: verifyRes.amount_rupees,
              finalTimestamp: verifyRes.captured_at || new Date().toISOString(),
              receiptUrl: verifyRes.receipt_url
            }));
            
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              sender: "AI ASSISTANT",
              text: `✅ Payment successful! Payment ID: ${response.razorpay_payment_id}`
            }]);
            
            await reloadCart();

            setTimeout(() => {
                setApprovalState('IDLE');
                setPendingPurchase(null);
                setPurchaseSteps([]);
                setIsCartOpen(false);
            }, 5000);
          }
        } catch (err: any) {
          setError(err.message || "Payment verification failed.");
          setApprovalState('IDLE');
          setPendingPurchase(null);
        }
      },
      modal: {
        ondismiss: function() {
           setApprovalState('IDLE');
           setPendingPurchase(null);
        }
      },
      prefill: {
        name: "Customer",
        email: "customer@example.com",
        contact: "9999999999"
      },
      theme: {
        color: "#4f46e5" // indigo-600
      }
    };

    const rzp1 = new window.Razorpay(options);
    rzp1.on('payment.failed', function (response: any){
      setError(`Payment Failed: ${response.error.description}`);
      setApprovalState('IDLE');
      setPendingPurchase(null);
    });
    rzp1.open();
  };

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-white">
      <BuyerHeader 
        cartItemCount={cart?.items?.length || 0}
        onCartClick={() => setIsCartOpen(true)}
      />


      <div className="flex flex-col md:flex-row flex-1 overflow-hidden">
        {/* AI Chat Area */}
        <div className="w-full md:w-1/3 md:min-w-[320px] md:max-w-[400px] h-1/2 md:h-full border-b md:border-b-0 md:border-r border-gray-200 shrink-0">
          <AiChat 
            messages={messages} 
            onSendMessage={handleSendMessage} 
            isLoading={isChatLoading} 
          />
        </div>

        {/* Products Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 bg-white relative">
          {error && (
            <div className="mb-6 p-4 bg-red-50 text-red-700 rounded-xl border border-red-100">
              {error}
            </div>
          )}

          <div className="max-w-5xl mx-auto space-y-8">
            <ProductResults 
              products={products}
              isLoading={isProductsLoading}
              onAddToCart={handleAddToCart}
              onBuyNow={handleBuyNow}
              onViewDetails={setSelectedProduct}
            />

            {recommendation && products.length > 0 && (
              <RecommendationCard 
                recommendation={recommendation}
                onAddToCart={handleAddToCart}
                onBuyNow={handleBuyNow}
              />
            )}
            
            {upsellSuggestions.length > 0 && (
              <div className="bg-indigo-50 border border-indigo-100 rounded-xl p-6 shadow-sm">
                <h3 className="text-lg font-bold text-indigo-900 mb-4 flex items-center">
                  <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  Frequently Bought Together
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {upsellSuggestions.map(upsell => (
                    <div key={upsell.id} className="bg-white p-4 rounded-lg border border-indigo-100 flex flex-col justify-between">
                      <div>
                        <h4 className="font-semibold text-gray-900 line-clamp-2 mb-1">{upsell.name}</h4>
                        <p className="text-sm text-gray-500 mb-3">{upsell.reason}</p>
                      </div>
                      <div className="flex items-center justify-between mt-4">
                        <span className="font-bold text-indigo-700">₹{upsell.price}</span>
                        <div className="flex gap-2">
                          <button 
                            onClick={() => handleUpsellResponse(upsell.id, 'decline')}
                            className="text-xs px-3 py-1.5 border border-gray-300 rounded text-gray-600 hover:bg-gray-50"
                          >
                            No Thanks
                          </button>
                          <button 
                            onClick={() => handleUpsellResponse(upsell.id, 'accept')}
                            className="text-xs px-3 py-1.5 bg-indigo-600 text-white rounded hover:bg-indigo-700"
                          >
                            Add to Order
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Agent Orchestration Area */}
        <div className="hidden lg:block w-[320px] h-full shrink-0 bg-slate-900 border-l border-slate-800">
          <AgentOrchestration 
            events={orchestrationEvents} 
            isExecuting={isChatLoading}
            error={null} 
          />
        </div>
      </div>

      <ProductDetails 
        product={selectedProduct}
        onClose={() => setSelectedProduct(null)}
        onAddToCart={handleAddToCart}
        onBuyNow={handleBuyNow}
      />

      <CartDrawer 
        isOpen={isCartOpen}
        onClose={() => setIsCartOpen(false)}
        cart={cart}
        onUpdateQuantity={handleUpdateCartItem}
        onRemove={handleRemoveCartItem}
        isLoading={isCartLoading}
        policyDecision={policyDecision}
        onInitiatePurchase={handleInitiatePurchase}
      />

      {approvalState !== 'IDLE' && pendingPurchase && (
        <div className="fixed inset-0 bg-gray-900/60 backdrop-blur-sm z-[70] flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full overflow-hidden border border-gray-100">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-100 bg-gray-50 flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-gray-900">Agent-Driven Purchase</h3>
            </div>
            
            <div className="p-6 space-y-6">
              {approvalState === 'WAITING_FOR_HUMAN_APPROVAL' && (
                <div className="space-y-4">
                  <h4 className="text-xl font-bold text-gray-900 text-center">Purchase Approval Required</h4>
                  <p className="text-gray-600 text-center text-sm">
                    The agent is ready to orchestrate this purchase for you. Please authorize the transaction below.
                  </p>
                  
                  <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                    {pendingPurchase.type === 'buy_now' ? (
                      <div className="flex justify-between items-center">
                        <span className="font-medium text-gray-800">{pendingPurchase.product.name}</span>
                        <span className="font-bold text-indigo-700">₹{pendingPurchase.product.price}</span>
                      </div>
                    ) : (
                      <>
                        {cart?.items?.map((item: any) => (
                          <div key={item.id} className="flex justify-between items-center text-sm py-1">
                            <span className="text-gray-700">{item.product?.name} x{item.quantity}</span>
                            <span className="font-medium text-gray-900">₹{(item.unit_price * item.quantity).toFixed(0)}</span>
                          </div>
                        ))}
                        <div className="border-t border-gray-200 mt-2 pt-2 flex justify-between items-center">
                          <span className="font-bold text-gray-900">Cart Total</span>
                          <span className="font-bold text-indigo-700">₹{Number(cart?.subtotal || 0).toFixed(0)}</span>
                        </div>
                      </>
                    )}
                  </div>
                  
                  <div className="flex gap-3 pt-2">
                    <button
                      onClick={handleCancelPurchase}
                      className="flex-1 px-4 py-2.5 bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 font-medium rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleApprovePurchase}
                      className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg shadow-sm transition-colors"
                    >
                      Approve Purchase
                    </button>
                  </div>
                </div>
              )}
              
              {approvalState === 'AGENT_PAYMENT_AUTHORIZED' && (
                <div className="py-8 flex flex-col items-center justify-center space-y-4">
                  <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h4 className="text-lg font-bold text-gray-900">Agent Payment Authorization Granted</h4>
                </div>
              )}
              
              {approvalState === 'AGENT_EXECUTING_PURCHASE' && (
                <div className="py-6 space-y-6">
                  <div className="flex flex-col items-center justify-center space-y-3">
                    <div className="w-10 h-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
                    <h4 className="text-base font-bold text-gray-900 text-center">Agent is executing your purchase...</h4>
                  </div>
                  
                  {/* GAP-2: Real streamed step events instead of hardcoded HTML */}
                  <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 space-y-2.5">
                    <h5 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Live Guardrail Checks</h5>
                    
                    {purchaseSteps.length === 0 && (
                      <p className="text-xs text-slate-400 italic">Awaiting first check...</p>
                    )}
                    
                    {purchaseSteps.map((step) => (
                      <div key={step.step} className="flex items-center justify-between text-sm">
                        <span className="text-slate-700 font-medium">{step.detail || step.step}</span>
                        <span className={`flex items-center font-semibold ml-2 shrink-0 ${
                          step.status === 'passed' ? 'text-green-600' :
                          step.status === 'blocked' ? 'text-red-600' :
                          'text-indigo-500'
                        }`}>
                          {step.status === 'passed' && (
                            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" /></svg>
                          )}
                          {step.status === 'blocked' && (
                            <svg className="w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                          )}
                          {step.status === 'running' && (
                            <div className="w-3 h-3 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin mr-1"></div>
                          )}
                          {step.status === 'passed' ? 'Pass' : step.status === 'blocked' ? 'Blocked' : 'Running'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {approvalState === 'PURCHASE_FAILED' && (
                <div className="py-6 space-y-6">
                  <div className="flex flex-col items-center justify-center space-y-4">
                    <div className="w-16 h-16 bg-red-100 text-red-600 rounded-full flex items-center justify-center">
                      <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                    </div>
                    <h4 className="text-lg font-bold text-gray-900 text-center">Purchase Blocked</h4>
                    <p className="text-sm text-gray-600 text-center px-4">
                      {error || "An error occurred while executing the purchase."}
                    </p>
                  </div>
                  
                  <div className="flex justify-center pt-2">
                    <button
                      onClick={handleCancelPurchase}
                      className="px-6 py-2.5 bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium rounded-lg transition-colors"
                    >
                      Close
                    </button>
                  </div>
                </div>
              )}

              {approvalState === 'RAZORPAY_PAYMENT_PROCESSING' && (
                <div className="py-8 flex flex-col items-center justify-center space-y-4">
                  <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
                  <h4 className="text-lg font-bold text-gray-900 text-center">Awaiting Razorpay Checkout</h4>
                  <p className="text-sm text-gray-500 text-center">Please complete the test payment in the Razorpay window.</p>
                </div>
              )}

              {approvalState === 'VERIFYING' && (
                <div className="py-8 flex flex-col items-center justify-center space-y-4">
                  <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                  <h4 className="text-lg font-bold text-gray-900 text-center">Verifying Payment...</h4>
                  <p className="text-sm text-gray-500 text-center">Validating actual payment signature with backend</p>
                </div>
              )}
              
              {approvalState === 'SUCCESS' && (
                <div className="py-8 flex flex-col items-center justify-center space-y-4">
                  <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center">
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h4 className="text-xl font-bold text-gray-900 text-center">Purchase Successful!</h4>
                  <div className="w-full bg-green-50 border border-green-200 rounded-xl p-4 space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-500">Payment ID</span>
                      <span className="font-mono text-gray-900 text-xs">{pendingPurchase.finalPaymentId}</span>
                    </div>
                    {pendingPurchase.finalAmount !== undefined && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Amount Paid</span>
                        <span className="font-bold text-green-700">₹{Number(pendingPurchase.finalAmount).toFixed(2)}</span>
                      </div>
                    )}
                    {pendingPurchase.finalTimestamp && (
                      <div className="flex justify-between">
                        <span className="text-gray-500">Captured At</span>
                        <span className="text-gray-700">{new Date(pendingPurchase.finalTimestamp).toLocaleString()}</span>
                      </div>
                    )}
                  </div>
                  {pendingPurchase.receiptUrl && (
                    <a
                      href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080/api'}${pendingPurchase.receiptUrl}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="w-full flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2.5 px-4 rounded-lg transition-colors text-sm"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span>View Receipt</span>
                    </a>
                  )}
                  <p className="text-xs text-gray-400">Closing automatically...</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

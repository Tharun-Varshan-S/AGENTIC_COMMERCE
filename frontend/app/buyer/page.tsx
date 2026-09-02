"use client";

declare global {
  interface Window {
    Razorpay: any;
  }
}

import { useState, useEffect } from "react";
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
  getAgenticAuthorizationStatus,
  executeAgenticPayment,
  executeDirectAgenticPayment,
  respondToUpsell
} from "@/lib/api";
import { useAuth } from "@/components/auth-provider";
import { BuyerHeader } from "@/components/buyer/buyer-header";
import { AiChat, Message } from "@/components/buyer/ai-chat";
import { ProductResults } from "@/components/buyer/product-results";
import { ProductDetails } from "@/components/buyer/product-details";
import { CartDrawer } from "@/components/buyer/cart-drawer";
import { RecommendationCard } from "@/components/buyer/recommendation-card";
import { AgenticPaymentSetup } from "@/components/buyer/agentic-payment-setup";

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
  const [isProcessingBuyNow, setIsProcessingBuyNow] = useState(false);
  const [agenticPurchaseTimeline, setAgenticPurchaseTimeline] = useState<string[]>([]);
  
  const { user, isLoading } = useAuth();

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

  const handleSendMessage = async (text: string) => {
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
        }
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
        if (response.checkout_session.agentic_paid) {
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              sender: "AI ASSISTANT",
              text: "✅ Agentic Payment successful! Your order has been placed securely without a manual checkout.",
              toolCalls: response.tool_calls
            }]);
            await reloadCart();
            setIsCartOpen(false);
            return; // skip the default agent text since we injected our own
        } else if (response.checkout_session.checkout_ready) {
            await reloadCart();
            setIsCartOpen(true);
        }
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

    // Check if agentic payment is active
    let hasAgenticAuth = false;
    try {
        const authStatus = await getAgenticAuthorizationStatus(merchantId);
        if (authStatus && authStatus.status === "ACTIVE") {
            hasAgenticAuth = true;
        }
    } catch(e) {}
    
    if (hasAgenticAuth) {
        setIsProcessingBuyNow(true);
        setAgenticPurchaseTimeline([
          "✓ Buyer authenticated",
          "✓ Agentic payment authorization verified",
          "⏳ Processing payment..."
        ]);
        try {
            const res = await executeDirectAgenticPayment(merchantId, product.offer_id, 1);
            setAgenticPurchaseTimeline([
              "✓ Buyer authenticated",
              "✓ Agentic payment authorization verified",
              "✓ Spending limit verified",
              "✓ Product availability verified",
              "✓ Payment initiated",
              "✓ Payment successful",
              `Order ID: ${res.order_number}`,
              `Payment ID: ${res.payment_id}`
            ]);
            setMessages(prev => [...prev, {
                id: Date.now().toString(),
                sender: "AI ASSISTANT",
                text: `✅ Purchase completed! Agentic Payment successful for ${product.name}.`
            }]);
            
            // Reload user limits
            const updateEvent = new CustomEvent('agentic-auth-update');
            window.dispatchEvent(updateEvent);

            setTimeout(() => {
                setIsProcessingBuyNow(false);
                setAgenticPurchaseTimeline([]);
            }, 4000);
            await reloadCart();
        } catch (err: any) {
            setAgenticPurchaseTimeline([]);
            setIsProcessingBuyNow(false);
            setError(`Agentic payment blocked: ${err.message}`);
        }
        return;
    }

    try {
      const orderRes = await createDirectPaymentOrder(merchantId, product.id, product.offer_id, 1);
      handleRazorpayCheckout(orderRes);
    } catch (err: any) {
      if (err.message && err.message.includes("Consent required")) {
         setError("This high-value order requires approval. Please add to cart to proceed with consent flow.");
      } else {
         setError(err.message);
      }
    }
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
    
    // Check if agentic payment is active
    let hasAgenticAuth = false;
    try {
        const authStatus = await getAgenticAuthorizationStatus(merchantId);
        if (authStatus && authStatus.status === "ACTIVE") {
            hasAgenticAuth = true;
        }
    } catch(e) {}
    
    const executeCheckout = async () => {
        if (hasAgenticAuth) {
             try {
                 await executeAgenticPayment(merchantId, cart.id);
                 setMessages(prev => [...prev, {
                     id: Date.now().toString(),
                     sender: "AI ASSISTANT",
                     text: "✅ Agentic Payment executed successfully after consent!"
                 }]);
                 await reloadCart();
                 setIsCartOpen(false);
             } catch(err: any) {
                 setError(err.message);
             }
        } else {
             try {
                 const orderRes = await createPaymentOrder(merchantId, cart.id);
                 handleRazorpayCheckout(orderRes);
             } catch(err: any) {
                 setError(err.message);
             }
        }
    };
    
    if (policyDecision?.decision === 'ALLOWED') {
        await executeCheckout();
        return;
    }
    
    if (policyDecision?.decision === 'REQUIRES_CONSENT') {
       try {
           setIsProcessingConsent(true);
           const res = await requestConsent(merchantId, cart.id);
           if (res.status === 'APPROVED') {
             setIsConsentModalOpen(false);
             setConsentRequest(null);
             await reloadCart();
             await executeCheckout();
           } else {
             setConsentRequest(res);
             setIsConsentModalOpen(true);
           }
       } catch (err: any) {
           setError("Failed to request consent");
       } finally {
           setIsProcessingConsent(false);
       }
    }
  };

  const handleApproveConsent = async () => {
    if (!consentRequest) return;
    setIsProcessingConsent(true);
    try {
        await approveConsent(consentRequest.id);
        setIsConsentModalOpen(false);
        setConsentRequest(null);
        await reloadCart();
        
        // Use the checkout logic
        let hasAgenticAuth = false;
        try {
            const authStatus = await getAgenticAuthorizationStatus(merchantId);
            if (authStatus && authStatus.status === "ACTIVE") {
                hasAgenticAuth = true;
            }
        } catch(e) {}
        
        if (hasAgenticAuth) {
             try {
                 await executeAgenticPayment(merchantId, cart.id);
                 setMessages(prev => [...prev, {
                     id: Date.now().toString(),
                     sender: "AI ASSISTANT",
                     text: "✅ Agentic Payment executed successfully after manual approval!"
                 }]);
                 await reloadCart();
                 setIsCartOpen(false);
             } catch(err: any) {
                 setError(err.message);
             }
        } else {
             const orderRes = await createPaymentOrder(merchantId, cart.id);
             handleRazorpayCheckout(orderRes);
        }
    } catch (err: any) {
        setError(err.message || "Failed to approve consent");
    } finally {
        setIsProcessingConsent(false);
    }
  };
  
  const handleDeclineConsent = () => {
    setIsConsentModalOpen(false);
    setConsentRequest(null);
  };

  const handleRazorpayCheckout = (paymentOrder: any) => {
    if (!window.Razorpay) {
      setError("Razorpay SDK failed to load. Are you offline?");
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
          const verifyRes = await verifyPayment(
            paymentOrder.payment_id,
            response.razorpay_payment_id,
            response.razorpay_order_id,
            response.razorpay_signature
          );
          
          if (verifyRes.status === "success") {
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              sender: "AI ASSISTANT",
              text: "✅ Payment successful! Your order has been placed."
            }]);
            
            // Clear cart logic here if we wanted to
            // For now just reload
            await reloadCart();
            setIsCartOpen(false);
          }
        } catch (err: any) {
          setError(err.message || "Payment verification failed.");
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
            {merchantId && (
               <AgenticPaymentSetup merchantId={merchantId} />
            )}
            
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

      {isConsentModalOpen && consentRequest && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm z-[60] flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-xl font-bold text-gray-900">Review Purchase</h3>
            </div>
            <div className="p-6 space-y-4">
              <div className="bg-gray-50 rounded-xl p-4 border border-gray-100 space-y-3">
                {cart?.items?.map((item: any) => (
                  <div key={item.id} className="flex justify-between items-center text-sm">
                    <span className="text-gray-700 font-medium">{item.product?.name} x{item.quantity}</span>
                    <span className="text-gray-900 font-semibold">₹{(item.unit_price * item.quantity).toFixed(0)}</span>
                  </div>
                ))}
                <div className="border-t border-gray-200 pt-3 flex justify-between items-center">
                  <span className="font-bold text-gray-900">Total</span>
                  <span className="text-lg font-bold text-indigo-700">₹{cart?.subtotal?.toFixed(0)}</span>
                </div>
              </div>
              
              <div className="p-4 bg-orange-50 rounded-xl border border-orange-100 text-orange-800 text-sm">
                <p className="font-bold mb-1">Merchant approval:</p>
                {consentRequest.reasons?.map((r: any, idx: number) => (
                   <p key={idx}>{r.message}</p>
                ))}
                {!consentRequest.reasons?.length && <p>Required above ₹3,000</p>}
              </div>
            </div>
            
            <div className="p-4 bg-gray-50 border-t border-gray-100 flex gap-3">
              <button
                onClick={handleDeclineConsent}
                disabled={isProcessingConsent}
                className="flex-1 px-4 py-2.5 bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 font-medium rounded-lg transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleApproveConsent}
                disabled={isProcessingConsent}
                className="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg shadow-sm shadow-indigo-200 transition-colors disabled:opacity-50 flex items-center justify-center"
              >
                {isProcessingConsent ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : "Approve Purchase"}
              </button>
            </div>
          </div>
        </div>
      )}

      {isProcessingBuyNow && (
        <div className="fixed inset-0 bg-gray-900/40 backdrop-blur-sm z-[70] flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-sm w-full overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-xl font-bold text-gray-900 text-center">Processing Agentic Payment</h3>
            </div>
            <div className="p-6">
              <div className="space-y-3">
                {agenticPurchaseTimeline.map((step, idx) => (
                  <div key={idx} className={`text-sm ${step.includes('✓') ? 'text-green-600 font-medium' : step.includes('Order ID') || step.includes('Payment ID') ? 'text-gray-500 font-mono text-xs' : 'text-gray-900 animate-pulse'}`}>
                    {step}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

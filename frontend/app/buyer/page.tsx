"use client";

import { useState, useEffect } from "react";
import { 
  fetchCustomers, 
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
  chatWithAgent
} from "@/lib/api";
import { BuyerHeader } from "@/components/buyer/buyer-header";
import { AiChat, Message } from "@/components/buyer/ai-chat";
import { ProductResults } from "@/components/buyer/product-results";
import { ProductDetails } from "@/components/buyer/product-details";
import { CartDrawer } from "@/components/buyer/cart-drawer";
import { RecommendationCard } from "@/components/buyer/recommendation-card";

export default function BuyerPage() {
  const [customers, setCustomers] = useState<any[]>([]);
  const [merchantId, setMerchantId] = useState<string>("");
  const [selectedCustomerId, setSelectedCustomerId] = useState<string>("");
  const [cart, setCart] = useState<any>(null);
  const [sessionId] = useState<string>(() => Date.now().toString());
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  
  const [products, setProducts] = useState<any[]>([]);
  const [isProductsLoading, setIsProductsLoading] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  
  const [recommendation, setRecommendation] = useState<any>(null);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isCartLoading, setIsCartLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Policy & Consent State
  const [policyDecision, setPolicyDecision] = useState<any>(null);
  const [consentRequest, setConsentRequest] = useState<any>(null);
  const [isConsentModalOpen, setIsConsentModalOpen] = useState(false);
  const [isProcessingConsent, setIsProcessingConsent] = useState(false);

  // Initialize
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [custs, merchants] = await Promise.all([
          fetchCustomers(),
          fetchMerchants()
        ]);
        setCustomers(custs);
        if (merchants && merchants.length > 0) {
          setMerchantId(merchants[0].id);
        }
      } catch (err) {
        setError("Unable to connect to the commerce service. Please try again.");
      }
    }
    loadInitialData();
  }, []);

  // Load cart and recommendations when customer changes
  useEffect(() => {
    if (!selectedCustomerId) return;
    
    async function loadCustomerData() {
      try {
        let activeCart = await fetchActiveCart(selectedCustomerId);
        if (!activeCart && merchantId) {
          activeCart = await createCart(selectedCustomerId, merchantId);
        }
        setCart(activeCart);
        setRecommendation(null);
        if (activeCart && activeCart.items && activeCart.items.length > 0) {
            checkPolicy(merchantId, selectedCustomerId, activeCart.id);
        } else {
            setPolicyDecision(null);
        }
      } catch (err) {
        console.error(err);
      }
    }
    loadCustomerData();
  }, [selectedCustomerId, merchantId]);

  const checkPolicy = async (mId: string, cId: string, cartId: string) => {
    try {
      const decision = await evaluatePolicy(mId, cId, cartId);
      setPolicyDecision(decision);
    } catch (err) {
      console.error("Failed to evaluate policy", err);
    }
  };

  const reloadCart = async () => {
    if (!selectedCustomerId) return;
    try {
      const activeCart = await fetchActiveCart(selectedCustomerId);
      setCart(activeCart);
      if (activeCart && activeCart.items && activeCart.items.length > 0) {
        checkPolicy(merchantId, selectedCustomerId, activeCart.id);
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

    try {
      const response = await chatWithAgent(sessionId, merchantId, selectedCustomerId, text);
      
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
      
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: "AI ASSISTANT",
        text: response.message,
        toolCalls: response.tool_calls
      }]);

    } catch (err) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: "AI ASSISTANT",
        text: "I'm having trouble connecting to the AI assistant right now. Please try again."
      }]);
    } finally {
      setIsChatLoading(false);
      setIsProductsLoading(false);
    }
  };

  const handleAddToCart = async (product: any) => {
    if (!selectedCustomerId || !cart) {
      alert("Please select a customer first.");
      return;
    }
    try {
      await addCartItem(cart.id, product.id, 1);
      await reloadCart();
    } catch (err: any) {
      setError(err.message);
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

  const handleInitiatePurchase = async () => {
    if (!cart) return;
    if (policyDecision?.decision === 'ALLOWED') {
       alert("Purchase successful! (Simulated)");
       return;
    }
    if (policyDecision?.decision === 'REQUIRES_CONSENT') {
       try {
           setIsProcessingConsent(true);
           const res = await requestConsent(merchantId, selectedCustomerId, cart.id);
           setConsentRequest(res);
           setIsConsentModalOpen(true);
       } catch (err: any) {
           setError("Failed to request consent");
       } finally {
           setIsProcessingConsent(false);
       }
    }
  };
  
  const handleApproveConsent = async () => {
      if (!consentRequest?.consent_id) return;
      try {
          setIsProcessingConsent(true);
          const res = await approveConsent(consentRequest.consent_id);
          if (res.status === 'APPROVED') {
              alert("Consent Approved! Purchase successful!");
              setIsConsentModalOpen(false);
              setConsentRequest(null);
              // Clean cart or just reload
              await reloadCart();
          } else {
              setError(res.message || "Failed to approve");
          }
      } catch (err: any) {
          setError(err.message);
      } finally {
          setIsProcessingConsent(false);
      }
  };
  
  const handleDeclineConsent = async () => {
      if (!consentRequest?.consent_id) {
          setIsConsentModalOpen(false);
          return;
      }
      try {
          setIsProcessingConsent(true);
          await declineConsent(consentRequest.consent_id);
          setIsConsentModalOpen(false);
          setConsentRequest(null);
      } catch (err: any) {
          setError(err.message);
      } finally {
          setIsProcessingConsent(false);
      }
  };

  return (
    <div className="flex flex-col h-screen bg-white">
      <BuyerHeader 
        customers={customers}
        selectedCustomerId={selectedCustomerId}
        onCustomerSelect={setSelectedCustomerId}
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
              onViewDetails={setSelectedProduct}
            />

            {recommendation && products.length > 0 && (
              <RecommendationCard 
                recommendation={recommendation}
                onAddToCart={handleAddToCart}
              />
            )}
          </div>
        </div>
      </div>

      <ProductDetails 
        product={selectedProduct}
        onClose={() => setSelectedProduct(null)}
        onAddToCart={handleAddToCart}
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
    </div>
  );
}

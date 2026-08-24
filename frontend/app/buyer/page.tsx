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
  fetchAgentDecisions,
  fetchMerchants,
  executeTool
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
  
  const [messages, setMessages] = useState<Message[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);
  
  const [products, setProducts] = useState<any[]>([]);
  const [isProductsLoading, setIsProductsLoading] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  
  const [recommendation, setRecommendation] = useState<any>(null);
  const [isCartOpen, setIsCartOpen] = useState(false);
  const [isCartLoading, setIsCartLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

        const decisions = await fetchAgentDecisions(selectedCustomerId);
        if (decisions && decisions.length > 0) {
          setRecommendation(decisions[0]);
        } else {
          setRecommendation(null);
        }
      } catch (err) {
        console.error(err);
      }
    }
    loadCustomerData();
  }, [selectedCustomerId, merchantId]);

  // Deterministic search parser
  const handleSendMessage = async (text: string) => {
    const newMessage: Message = { id: Date.now().toString(), sender: "USER", text };
    setMessages(prev => [...prev, newMessage]);
    setIsChatLoading(true);
    setIsProductsLoading(true);
    setError(null);

    try {
      // Very simple deterministic parser
      const lowerText = text.toLowerCase();
      let search = "";
      let maxPrice: number | undefined;
      let category = "";

      if (lowerText.includes("mouse")) search = "mouse";
      if (lowerText.includes("keyboard")) search = "keyboard";
      if (lowerText.includes("headset")) search = "headset";
      if (lowerText.includes("monitor")) search = "monitor";

      const priceMatch = lowerText.match(/under\s*(?:rs\.?|₹)?\s*(\d+)/i);
      if (priceMatch && priceMatch[1]) {
        maxPrice = parseInt(priceMatch[1], 10);
      }

      if (lowerText.includes("gaming")) {
        category = "Gaming";
      } else if (lowerText.includes("audio")) {
        category = "Audio";
      } else if (lowerText.includes("accessories")) {
        category = "Accessories";
      }

      const toolResult = await executeTool("search_catalog", {
        merchant_id: merchantId,
        query: search || undefined,
        category: category || undefined,
        max_price: maxPrice
      });
      
      const results = toolResult.result?.products || [];
      setProducts(results);

      let aiResponseText = "";
      if (results.length > 0) {
        aiResponseText = `I found ${results.length} product(s) matching your requirements.`;
        if (maxPrice) {
          aiResponseText = `I found ${results.length} option(s) under ₹${maxPrice}.`;
        }
        aiResponseText += `\n\nI've displayed them for you to review. Let me know if you want to refine this search.`;
      } else {
        aiResponseText = `I couldn't find any products matching that exactly. Try changing your budget or search terms.`;
      }

      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: "AI ASSISTANT",
        text: aiResponseText
      }]);

    } catch (err) {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: "AI ASSISTANT",
        text: "I'm having trouble connecting to the product catalog right now. Please try again."
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
    
    setIsCartLoading(true);
    try {
      const updatedCart = await addCartItem(cart.id, product.id, 1);
      setCart(updatedCart);
      setIsCartOpen(true);
    } catch (err: any) {
      alert(err.message || "Failed to add to cart");
    } finally {
      setIsCartLoading(false);
    }
  };

  const handleUpdateQuantity = async (itemId: string, quantity: number) => {
    setIsCartLoading(true);
    try {
      const updatedCart = await updateCartItem(cart.id, itemId, quantity);
      setCart(updatedCart);
    } catch (err: any) {
      alert(err.message || "Failed to update quantity");
    } finally {
      setIsCartLoading(false);
    }
  };

  const handleRemoveItem = async (itemId: string) => {
    setIsCartLoading(true);
    try {
      const updatedCart = await removeCartItem(cart.id, itemId);
      setCart(updatedCart);
    } catch (err: any) {
      alert(err.message || "Failed to remove item");
    } finally {
      setIsCartLoading(false);
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
        onUpdateQuantity={handleUpdateQuantity}
        onRemove={handleRemoveItem}
        isLoading={isCartLoading}
      />
    </div>
  );
}

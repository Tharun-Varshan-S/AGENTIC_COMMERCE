"use client";

import { X, Minus, Plus, Trash2 } from "lucide-react";

type CartItemProps = {
  item: any;
  onUpdateQuantity: (itemId: string, quantity: number) => void;
  onRemove: (itemId: string) => void;
};

function CartItem({ item, onUpdateQuantity, onRemove }: CartItemProps) {
  const formatPrice = (price: string | number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(price));
  };

  const product = item.product || {};
  const isAvailable = product.inventory && product.inventory.available_quantity > 0;
  
  return (
    <div className="flex gap-4 py-4 border-b border-gray-100 last:border-0">
      <div className="flex-1">
        <h4 className="font-semibold text-gray-900 leading-tight mb-1">
          {product.name || "Unknown Product"}
        </h4>
        <p className="text-sm font-medium text-gray-500 mb-3">
          {formatPrice(item.unit_price)}
        </p>
        
        <div className="flex items-center gap-4">
          <div className="flex items-center bg-gray-50 border border-gray-200 rounded-lg">
            <button
              onClick={() => onUpdateQuantity(item.id, item.quantity - 1)}
              className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-l-lg transition-colors"
              disabled={item.quantity <= 1}
            >
              <Minus className="w-4 h-4" />
            </button>
            <span className="w-8 text-center text-sm font-medium text-gray-900">
              {item.quantity}
            </span>
            <button
              onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
              className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-r-lg transition-colors disabled:opacity-50"
              disabled={!isAvailable || item.quantity >= (product.inventory?.available_quantity || 1)}
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <button
            onClick={() => onRemove(item.id)}
            className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
      <div className="text-right">
        <p className="font-semibold text-gray-900">
          {formatPrice(Number(item.unit_price) * item.quantity)}
        </p>
      </div>
    </div>
  );
}

type CartDrawerProps = {
  isOpen: boolean;
  onClose: () => void;
  cart: any;
  onUpdateQuantity: (itemId: string, quantity: number) => void;
  onRemove: (itemId: string) => void;
  isLoading: boolean;
  policyDecision?: any;
  onInitiatePurchase?: () => void;
};

export function CartDrawer({
  isOpen,
  onClose,
  cart,
  onUpdateQuantity,
  onRemove,
  isLoading,
  policyDecision,
  onInitiatePurchase
}: CartDrawerProps) {
  if (!isOpen) return null;

  const formatPrice = (price: string | number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(price));
  };

  const hasItems = cart && cart.items && cart.items.length > 0;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-gray-900/20 backdrop-blur-sm z-40"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-2xl flex flex-col transform transition-transform duration-300 ease-in-out">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-white">
          <h2 className="text-xl font-bold text-gray-900">Your Cart</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 relative">
          {isLoading && (
            <div className="absolute inset-0 bg-white/50 backdrop-blur-[1px] flex items-center justify-center z-10">
              <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}
          
          {!hasItems ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 space-y-4">
              <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center">
                <ShoppingCart className="w-8 h-8 text-gray-300" />
              </div>
              <p className="font-medium text-gray-900">Your cart is empty</p>
              <p className="text-sm">Find something amazing to add.</p>
            </div>
          ) : (
            <div className="flex flex-col">
              {cart.items.map((item: any) => (
                <CartItem 
                  key={item.id} 
                  item={item} 
                  onUpdateQuantity={onUpdateQuantity}
                  onRemove={onRemove}
                />
              ))}
            </div>
          )}
        </div>

        {hasItems && (
          <div className="border-t border-gray-100 bg-gray-50 p-6 space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-600 font-medium">Subtotal</span>
              <span className="text-xl font-bold text-gray-900">
                {formatPrice(cart.subtotal || 0)}
              </span>
            </div>
            
            {policyDecision && policyDecision.decision === 'ALLOWED' && (
              <div className="p-3 bg-green-50 border border-green-100 rounded-lg text-green-700 text-sm font-medium flex items-center gap-2">
                ✓ Purchase can proceed
              </div>
            )}
            
            {policyDecision && policyDecision.decision === 'REQUIRES_CONSENT' && (
              <div className="p-4 bg-orange-50 border border-orange-100 rounded-lg text-orange-800 text-sm">
                <p className="font-bold mb-2">Customer approval required</p>
                <p className="mb-2">Your cart total is {formatPrice(cart.subtotal || 0)}.</p>
                {policyDecision.reasons?.map((r: any, idx: number) => (
                  <p key={idx} className="mb-1 text-orange-700">{r.message}</p>
                ))}
              </div>
            )}
            
            {policyDecision && policyDecision.decision === 'REJECTED' && (
              <div className="p-4 bg-red-50 border border-red-100 rounded-lg text-red-800 text-sm">
                <p className="font-bold mb-2">Purchase cannot proceed</p>
                <p className="font-semibold mt-2 mb-1">Reason:</p>
                {policyDecision.reasons?.map((r: any, idx: number) => (
                  <p key={idx} className="mb-1 text-red-700">- {r.message}</p>
                ))}
              </div>
            )}

            <div className="flex flex-col gap-2 pt-2">
                {policyDecision?.decision === 'REJECTED' ? (
                     <button disabled className="w-full py-3.5 px-4 bg-gray-300 text-gray-500 font-medium rounded-xl flex items-center justify-center cursor-not-allowed">
                        Cannot Proceed
                     </button>
                ) : (
                    <button 
                      onClick={onInitiatePurchase}
                      className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl shadow-sm shadow-indigo-200 transition-colors flex items-center justify-center"
                    >
                      {policyDecision?.decision === 'REQUIRES_CONSENT' ? 'Confirm Purchase' : 'Purchase'}
                    </button>
                )}
                {policyDecision?.decision === 'REQUIRES_CONSENT' && (
                    <button 
                      onClick={onClose}
                      className="w-full py-3.5 px-4 bg-white border border-gray-200 text-gray-700 hover:bg-gray-50 font-medium rounded-xl transition-colors flex items-center justify-center"
                    >
                      Review Cart
                    </button>
                )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

function ShoppingCart(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="8" cy="21" r="1" />
      <circle cx="19" cy="21" r="1" />
      <path d="M2.05 2.05h2l2.66 12.42a2 2 0 0 0 2 1.58h9.78a2 2 0 0 0 1.95-1.57l1.65-7.43H5.12" />
    </svg>
  );
}

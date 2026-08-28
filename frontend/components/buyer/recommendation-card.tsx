"use client";

import { Sparkles, ShoppingBag } from "lucide-react";

type RecommendationProps = {
  recommendation: any;
  onAddToCart: (product: any) => void;
  onBuyNow?: (product: any) => void;
};

export function RecommendationCard({ recommendation, onAddToCart, onBuyNow }: RecommendationProps) {
  if (!recommendation || !recommendation.recommended_product) return null;

  const product = recommendation.recommended_product;
  const isAvailable = product.inventory && product.inventory.available_quantity > 0;

  const formatPrice = (price: string | number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(price));
  };

  return (
    <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-100 rounded-2xl p-5 shadow-sm relative overflow-hidden mt-6">
      <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
        <Sparkles className="w-24 h-24 text-indigo-600" />
      </div>
      
      <div className="flex items-center gap-2 text-indigo-700 font-semibold mb-4 relative z-10">
        <Sparkles className="w-5 h-5" />
        AI Recommendation
      </div>

      <div className="bg-white rounded-xl p-4 border border-indigo-100/50 shadow-sm relative z-10 flex flex-col md:flex-row gap-4 items-start md:items-center">
        <div className="flex-1">
          <p className="text-sm text-gray-500 mb-1">You may also need:</p>
          <h4 className="text-lg font-bold text-gray-900">{product.name}</h4>
          <p className="text-xl font-bold text-gray-900 mt-1">{formatPrice(product.price)}</p>
          
          {recommendation.reason && (
            <div className="mt-3 text-sm text-indigo-900 bg-indigo-50/50 p-2 rounded-lg border border-indigo-100">
              <span className="font-semibold block mb-0.5">Why?</span>
              {recommendation.reason}
            </div>
          )}
        </div>

        <div className="flex gap-2 w-full md:w-auto mt-4 md:mt-0">
          <button
            onClick={() => onAddToCart(product)}
            disabled={!isAvailable}
            className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-xl hover:bg-gray-50 transition-colors"
          >
            <ShoppingBag className="w-4 h-4" />
            Add
          </button>
          <button
            onClick={() => onBuyNow ? onBuyNow(product) : onAddToCart(product)}
            disabled={!isAvailable}
            className="flex-1 md:flex-none flex items-center justify-center gap-2 px-6 py-2.5 text-sm font-medium text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-colors shadow-sm shadow-indigo-200"
          >
            Buy Now
          </button>
        </div>
      </div>
    </div>
  );
}

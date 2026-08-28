"use client";

import { ShoppingBag } from "lucide-react";

type Inventory = {
  available_quantity: number;
};

type Product = {
  id: string;
  offer_id?: string;
  name: string;
  description?: string;
  category: string;
  brand?: string;
  price: string | number;
  mrp?: string | number;
  image_url?: string;
  inventory?: Inventory;
  source?: string;
  rating?: number | string;
  review_count?: number;
  is_sponsored?: boolean;
  delivery_estimate?: string;
};

type ProductCardProps = {
  product: Product;
  onAddToCart: (product: Product) => void;
  onBuyNow?: (product: Product) => void;
  onViewDetails: (product: Product) => void;
};

export function ProductCard({ product, onAddToCart, onBuyNow, onViewDetails }: ProductCardProps) {
  const formatPrice = (price: string | number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(price));
  };

  const isAvailable = product.inventory ? product.inventory.available_quantity > 0 : true;
  const isLowStock = product.inventory ? product.inventory.available_quantity < 10 : false;

  const getSourceBadge = (source?: string) => {
    switch (source?.toLowerCase()) {
      case "amazon":
        return <div className="flex flex-col items-end"><span className="text-[10px] font-bold text-gray-900 bg-[#FF9900]/20 px-2 py-0.5 rounded">Amazon</span><span className="text-[8px] text-gray-500 uppercase mt-0.5">(Demo Source)</span></div>;
      case "flipkart":
        return <div className="flex flex-col items-end"><span className="text-[10px] font-bold text-white bg-[#2874f0] px-2 py-0.5 rounded">Flipkart</span><span className="text-[8px] text-gray-500 uppercase mt-0.5">(Demo Source)</span></div>;
      case "razorpay":
      default:
        return <span className="text-[10px] font-bold text-white bg-indigo-600 px-2 py-0.5 rounded">TechNova</span>;
    }
  };

  const calculateDiscount = (price: number, mrp: number) => {
    if (mrp <= price) return 0;
    return Math.round(((mrp - price) / mrp) * 100);
  };

  return (
    <div className={`flex flex-col bg-white border ${product.is_sponsored ? 'border-amber-300 ring-1 ring-amber-300' : 'border-gray-100'} rounded-xl shadow-sm hover:shadow-lg transition-all duration-300 overflow-hidden relative group`}>
      {product.is_sponsored && (
        <div className="absolute top-0 right-0 z-10 bg-gradient-to-r from-amber-200 to-amber-100 text-amber-800 text-[10px] font-bold px-3 py-1 rounded-bl-lg shadow-sm">
          Sponsored
        </div>
      )}
      
      {/* Product Image Area */}
      <div className="relative w-full h-48 bg-gray-50 overflow-hidden cursor-pointer" onClick={() => onViewDetails(product)}>
        {product.image_url ? (
          <img src={product.image_url} alt={product.name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-300">
            <ShoppingBag className="w-12 h-12 opacity-20" />
          </div>
        )}
        <div className="absolute top-3 right-3">
          {getSourceBadge(product.source)}
        </div>
      </div>

      <div className="p-4 flex-1 flex flex-col">
        <p className="text-[10px] font-semibold tracking-wider text-indigo-600 uppercase mb-1">
          {product.category}
        </p>
        
        <h3 
          className="text-base font-bold text-gray-900 leading-tight mb-2 line-clamp-2 cursor-pointer hover:text-indigo-600 transition-colors"
          onClick={() => onViewDetails(product)}
        >
          {product.name}
        </h3>

        {product.rating && (
          <div className="flex items-center gap-1 mb-2">
            <span className="text-amber-500 text-sm">★</span>
            <span className="text-sm font-bold text-gray-700">{Number(product.rating).toFixed(1)}</span>
            <span className="text-xs text-gray-500">({product.review_count || 0})</span>
          </div>
        )}
        
        <div className="mt-1 flex items-baseline gap-2">
          <p className="text-xl font-bold text-gray-900">
            {formatPrice(product.price)}
          </p>
          {product.mrp && Number(product.mrp) > Number(product.price) && (
            <>
              <p className="text-sm text-gray-400 line-through">
                {formatPrice(product.mrp)}
              </p>
              <p className="text-xs font-bold text-green-600 bg-green-50 px-1.5 py-0.5 rounded">
                {calculateDiscount(Number(product.price), Number(product.mrp))}% OFF
              </p>
            </>
          )}
        </div>
        
        {product.delivery_estimate && (
          <p className="text-xs text-gray-600 font-medium mb-4">
            Delivery: <span className="text-emerald-700">{product.delivery_estimate}</span>
          </p>
        )}

        {product.inventory && (
          <div className="flex items-center text-sm font-medium mt-auto">
            {!isAvailable ? (
              <span className="flex items-center text-red-600">
                <span className="w-2 h-2 rounded-full bg-red-600 mr-2"></span>
                Out of stock
              </span>
            ) : isLowStock ? (
              <span className="flex items-center text-orange-600">
                <span className="w-2 h-2 rounded-full bg-orange-500 mr-2"></span>
                Only {product.inventory.available_quantity} left
              </span>
            ) : null}
          </div>
        )}
      </div>

      <div className="p-3 bg-gray-50 flex gap-2 border-t border-gray-100 mt-auto">
        <button
          onClick={() => onAddToCart(product)}
          disabled={!isAvailable}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50"
        >
          Add to Cart
        </button>
        <button
          onClick={() => onBuyNow ? onBuyNow(product) : onAddToCart(product)}
          disabled={!isAvailable}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 shadow-sm transition-colors disabled:opacity-50"
        >
          Buy Now
        </button>
      </div>
    </div>
  );
}

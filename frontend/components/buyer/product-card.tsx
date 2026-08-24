"use client";

import { ShoppingBag } from "lucide-react";

type Inventory = {
  available_quantity: number;
};

type Product = {
  id: string;
  name: string;
  description: string;
  category: string;
  brand: string;
  price: string | number;
  inventory?: Inventory;
};

type ProductCardProps = {
  product: Product;
  onAddToCart: (product: Product) => void;
  onViewDetails: (product: Product) => void;
};

export function ProductCard({ product, onAddToCart, onViewDetails }: ProductCardProps) {
  const formatPrice = (price: string | number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(price));
  };

  const isAvailable = product.inventory && product.inventory.available_quantity > 0;
  const isLowStock = isAvailable && product.inventory!.available_quantity < 10;

  return (
    <div className="flex flex-col bg-white border border-gray-100 rounded-2xl shadow-sm hover:shadow-md transition-shadow overflow-hidden">
      <div className="p-5 flex-1">
        <div className="flex justify-between items-start mb-2">
          <p className="text-xs font-semibold tracking-wider text-indigo-600 uppercase">
            {product.category}
          </p>
          <span className="text-xs font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded-md">
            {product.brand}
          </span>
        </div>
        
        <h3 className="text-lg font-bold text-gray-900 leading-tight mb-2">
          {product.name}
        </h3>
        
        <p className="text-2xl font-bold text-gray-900 mb-4">
          {formatPrice(product.price)}
        </p>

        <div className="flex items-center text-sm font-medium">
          {!isAvailable ? (
            <span className="flex items-center text-red-600">
              <span className="w-2 h-2 rounded-full bg-red-600 mr-2"></span>
              Out of stock
            </span>
          ) : isLowStock ? (
            <span className="flex items-center text-orange-600">
              <span className="w-2 h-2 rounded-full bg-orange-500 mr-2"></span>
              Only {product.inventory?.available_quantity} left
            </span>
          ) : (
            <span className="flex items-center text-emerald-600">
              <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2"></span>
              In stock
            </span>
          )}
        </div>
      </div>

      <div className="p-3 bg-gray-50 flex gap-2 border-t border-gray-100">
        <button
          onClick={() => onViewDetails(product)}
          className="flex-1 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
        >
          View Details
        </button>
        <button
          onClick={() => onAddToCart(product)}
          disabled={!isAvailable}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-colors"
        >
          <ShoppingBag className="w-4 h-4" />
          Add
        </button>
      </div>
    </div>
  );
}

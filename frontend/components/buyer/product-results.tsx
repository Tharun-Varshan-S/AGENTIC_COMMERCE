"use client";

import { ProductCard } from "./product-card";
import { PackageX } from "lucide-react";

type ProductResultsProps = {
  products: any[];
  isLoading: boolean;
  onAddToCart: (product: any) => void;
  onViewDetails: (product: any) => void;
};

export function ProductResults({ products, isLoading, onAddToCart, onViewDetails }: ProductResultsProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white border border-gray-100 rounded-2xl p-5 shadow-sm animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
            <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
            <div className="h-10 bg-gray-200 rounded w-full"></div>
          </div>
        ))}
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-500">
        <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mb-4">
          <PackageX className="w-8 h-8 text-gray-300" />
        </div>
        <p className="text-lg font-medium text-gray-900">No products found</p>
        <p className="text-sm">Try adjusting your search criteria</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {products.map((product) => (
        <ProductCard
          key={product.id}
          product={product}
          onAddToCart={onAddToCart}
          onViewDetails={onViewDetails}
        />
      ))}
    </div>
  );
}

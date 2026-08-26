"use client";

import { X, ShoppingBag, Package } from "lucide-react";

type ProductDetailsProps = {
  product: any;
  onClose: () => void;
  onAddToCart: (product: any) => void;
};

export function ProductDetails({ product, onClose, onAddToCart }: ProductDetailsProps) {
  if (!product) return null;

  const formatPrice = (price: string | number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(Number(price));
  };

  const calculateDiscount = (price: number, mrp: number) => {
    if (mrp <= price) return 0;
    return Math.round(((mrp - price) / mrp) * 100);
  };

  const isAvailable = product.inventory && product.inventory.available_quantity > 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="text-xl font-bold text-gray-900">Product Details</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto">
          <div className="flex flex-col md:flex-row gap-8">
            
            {/* Image Column */}
            <div className="w-full md:w-1/2 flex-shrink-0">
              <div className="aspect-square bg-gray-50 rounded-xl overflow-hidden border border-gray-100 flex items-center justify-center relative">
                {product.image_url ? (
                  <img src={product.image_url} alt={product.name} className="w-full h-full object-cover" />
                ) : (
                  <ShoppingBag className="w-24 h-24 text-gray-200" />
                )}
                {product.is_sponsored && (
                  <div className="absolute top-0 right-0 bg-amber-100 text-amber-800 text-[10px] font-bold px-3 py-1 rounded-bl-lg">
                    Sponsored
                  </div>
                )}
              </div>
            </div>

            {/* Content Column */}
            <div className="flex-1 flex flex-col space-y-6">
              <div>
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-sm font-semibold tracking-wider text-indigo-600 uppercase">
                    {product.category}
                  </span>
                  <span className="text-sm font-medium text-gray-500 bg-gray-100 px-2 py-1 rounded-md">
                    {product.brand}
                  </span>
                </div>
                <h1 className="text-3xl font-bold text-gray-900 leading-tight mb-2">
                  {product.name}
                </h1>
                <p className="text-sm text-gray-500 font-mono">SKU: {product.sku}</p>
              </div>

              <div className="flex items-baseline gap-3">
                <p className="text-4xl font-bold text-gray-900">
                  {formatPrice(product.price)}
                </p>
                {product.mrp && Number(product.mrp) > Number(product.price) && (
                  <>
                    <p className="text-lg text-gray-400 line-through">
                      {formatPrice(product.mrp)}
                    </p>
                    <p className="text-sm font-bold text-green-600 bg-green-50 px-2 py-1 rounded">
                      {calculateDiscount(Number(product.price), Number(product.mrp))}% OFF
                    </p>
                  </>
                )}
              </div>

              <div className="prose prose-sm text-gray-600">
                <p>{product.description}</p>
              </div>

              <div className="flex items-center gap-4 py-4 border-y border-gray-100">
                <div className="flex items-center gap-2 text-gray-600">
                  <Package className="w-5 h-5 text-gray-400" />
                  <span className="font-medium">Inventory:</span>
                </div>
                {isAvailable ? (
                  <span className="text-emerald-600 font-medium bg-emerald-50 px-3 py-1 rounded-full text-sm">
                    {product.inventory.available_quantity} units available
                  </span>
                ) : (
                  <span className="text-red-600 font-medium bg-red-50 px-3 py-1 rounded-full text-sm">
                    Out of stock
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-6 py-2.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-xl hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
          <button
            onClick={() => {
              onAddToCart(product);
              onClose();
            }}
            disabled={!isAvailable}
            className="flex items-center gap-2 px-8 py-2.5 text-sm font-medium text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-colors shadow-sm shadow-indigo-200"
          >
            <ShoppingBag className="w-5 h-5" />
            Buy Now
          </button>
        </div>
      </div>
    </div>
  );
}

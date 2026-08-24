"use client";

import { ShoppingCart, Bot } from "lucide-react";

type Customer = {
  id: string;
  name: string;
};

type BuyerHeaderProps = {
  customers: Customer[];
  selectedCustomerId: string;
  onCustomerSelect: (id: string) => void;
  cartItemCount: number;
  onCartClick: () => void;
};

export function BuyerHeader({
  customers,
  selectedCustomerId,
  onCustomerSelect,
  cartItemCount,
  onCartClick,
}: BuyerHeaderProps) {
  return (
    <header className="sticky top-0 z-10 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <div className="flex items-center space-x-3 text-indigo-600">
        <Bot className="w-6 h-6" />
        <h1 className="text-xl font-semibold text-gray-900 tracking-tight">
          TechNova <span className="text-indigo-600">AI Commerce</span>
        </h1>
      </div>

      <div className="flex items-center space-x-6">
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <span>Shopping as:</span>
          <select
            className="border-gray-300 rounded-md shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50"
            value={selectedCustomerId}
            onChange={(e) => onCustomerSelect(e.target.value)}
          >
            <option value="" disabled>Select customer...</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={onCartClick}
          className="relative p-2 text-gray-600 hover:text-indigo-600 transition-colors"
        >
          <ShoppingCart className="w-6 h-6" />
          {cartItemCount > 0 && (
            <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full">
              {cartItemCount}
            </span>
          )}
        </button>
      </div>
    </header>
  );
}

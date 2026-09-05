"use client";

import { ShoppingCart, Bot, History, UserCircle } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import Link from "next/link";

type BuyerHeaderProps = {
  cartItemCount: number;
  onCartClick: () => void;
};

export function BuyerHeader({
  cartItemCount,
  onCartClick,
}: BuyerHeaderProps) {
  const { user } = useAuth();
  
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
          <span className="font-medium text-gray-900">{user?.full_name || user?.email || "Guest"}</span>
        </div>

        <Link 
          href="/buyer/history"
          className="p-2 text-gray-600 hover:text-indigo-600 transition-colors"
          title="Payment History"
        >
          <History className="w-6 h-6" />
        </Link>

        <Link
          href="/buyer/profile"
          className="p-2 text-gray-600 hover:text-indigo-600 transition-colors"
          title="Profile & Spending Limits"
        >
          <UserCircle className="w-6 h-6" />
        </Link>

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

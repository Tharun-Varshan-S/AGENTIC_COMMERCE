"use client";

import React from "react";

export default function MerchantLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900 w-full">
      {/* Sidebar - hidden on mobile */}
      <aside className="w-64 bg-slate-900 text-white hidden md:flex flex-col">
        <div className="h-16 flex items-center px-6 font-bold text-lg border-b border-slate-800">
          Agentic Commerce
        </div>
        <nav className="flex-1 py-4 px-3 space-y-1">
          <a href="#" className="bg-indigo-600 text-white group flex items-center px-3 py-2 text-sm font-medium rounded-md">
            Dashboard
          </a>
          <a href="#" className="text-slate-300 hover:bg-slate-800 hover:text-white group flex items-center px-3 py-2 text-sm font-medium rounded-md">
            Orders
          </a>
          <a href="#" className="text-slate-300 hover:bg-slate-800 hover:text-white group flex items-center px-3 py-2 text-sm font-medium rounded-md">
            Products
          </a>
          <a href="#" className="text-slate-300 hover:bg-slate-800 hover:text-white group flex items-center px-3 py-2 text-sm font-medium rounded-md">
            Agent Rules
          </a>
        </nav>
        <div className="p-4 border-t border-slate-800 text-sm text-slate-400">
          <p>TechNova Gaming</p>
          <p className="text-xs mt-1">Status: Active</p>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-4 md:px-6 justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button className="md:hidden p-2 text-slate-600 hover:bg-slate-100 rounded-md">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>
            </button>
            <h1 className="text-lg md:text-xl font-semibold text-slate-800">Merchant Dashboard</h1>
          </div>
          <div className="flex items-center space-x-4">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 text-indigo-700 font-medium text-sm md:text-base">
              TN
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

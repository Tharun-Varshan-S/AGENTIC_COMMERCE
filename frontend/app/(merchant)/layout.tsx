"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, ShoppingCart, Box, Settings, Activity, BrainCircuit, RefreshCcw } from "lucide-react";
import { API_BASE } from "@/lib/api";

export default function MerchantLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [isResetting, setIsResetting] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const handleReset = async () => {
    if (confirm("Are you sure you want to reset demo data? This will wipe the database and re-seed it.")) {
      setIsResetting(true);
      try {
        const res = await fetch(`${API_BASE}/demo/reset`, { method: "POST" });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to reset");
        }
        alert("Demo state reset successfully!");
        window.location.reload();
      } catch (err: any) {
        alert(`Error: ${err.message}`);
      } finally {
        setIsResetting(false);
      }
    }
  };

  const navItems = [
    { name: "Dashboard", href: "/", icon: <LayoutDashboard className="w-5 h-5 mr-3" /> },
    { name: "Agent Activity", href: "/activity", icon: <Activity className="w-5 h-5 mr-3" /> },
    { name: "Decision Explorer", href: "/decisions", icon: <BrainCircuit className="w-5 h-5 mr-3" /> },
    { name: "Orders", href: "/orders", icon: <ShoppingCart className="w-5 h-5 mr-3" /> },
    { name: "Products", href: "/products", icon: <Box className="w-5 h-5 mr-3" /> },
    { name: "Agent Rules", href: "/rules", icon: <Settings className="w-5 h-5 mr-3" /> },
  ];

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 text-slate-900 w-full relative">
      {/* Mobile overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/50 z-40 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className={`bg-slate-900 text-white z-50 transition-all duration-300 shrink-0 h-full fixed md:relative ${
          isSidebarOpen ? 'w-64 translate-x-0' : 'w-0 -translate-x-full md:translate-x-0 md:w-0'
        } overflow-hidden`}
      >
        <div className="w-64 flex flex-col h-full">
          <div className="h-16 flex items-center px-6 font-bold text-lg border-b border-slate-800 shrink-0">
            Agentic Commerce
          </div>
          <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
            {navItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link 
                  key={item.name} 
                  href={item.href}
                  className={`${isActive ? 'bg-indigo-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'} group flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors`}
                >
                  {item.icon}
                  {item.name}
                </Link>
              );
            })}
          </nav>
          <div className="p-4 border-t border-slate-800 text-sm text-slate-400 space-y-3 shrink-0">
            <div>
              <p className="font-semibold text-slate-200">TechNova Gaming</p>
              <p className="text-xs mt-0.5">Status: Active Demo</p>
            </div>
            <button 
              onClick={handleReset}
              disabled={isResetting}
              className="w-full flex items-center justify-center gap-2 bg-slate-800 hover:bg-red-900/50 text-slate-300 hover:text-red-400 border border-slate-700 hover:border-red-800 py-1.5 px-3 rounded text-xs font-medium transition-all disabled:opacity-50"
            >
              <RefreshCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
              {isResetting ? 'Resetting...' : 'Reset Demo Data'}
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden w-full">
        <header className="h-16 bg-white border-b border-slate-200 flex items-center px-4 md:px-6 justify-between shrink-0">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
            >
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

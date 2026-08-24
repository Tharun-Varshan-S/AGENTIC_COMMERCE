"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Activity, ServerCrash, Store, Package, Users } from "lucide-react";

export default function Home() {
  const [status, setStatus] = useState<"loading" | "connected" | "error">("loading");
  const [service, setService] = useState<string>("");
  const [stats, setStats] = useState({ merchants: 0, products: 0, customers: 0 });

  useEffect(() => {
    const fetchData = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        
        // Health check
        const res = await fetch(`${apiUrl}/api/health`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === "ok") {
            setStatus("connected");
            setService(data.service);
            
            // Fetch stats
            const [mRes, pRes, cRes] = await Promise.all([
              fetch(`${apiUrl}/api/merchants`),
              fetch(`${apiUrl}/api/products`),
              fetch(`${apiUrl}/api/customers`)
            ]);
            
            if (mRes.ok && pRes.ok && cRes.ok) {
              const merchants = await mRes.json();
              const products = await pRes.json();
              const customers = await cRes.json();
              
              setStats({
                merchants: merchants.length,
                products: products.length,
                customers: customers.length
              });
            }
          } else {
            setStatus("error");
          }
        } else {
          setStatus("error");
        }
      } catch (err) {
        console.error("Fetch failed", err);
        setStatus("error");
      }
    };

    fetchData();
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-black text-white p-4">
      <div className="max-w-md w-full bg-zinc-900 border border-zinc-800 rounded-xl shadow-2xl p-8 space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
            Razorpay MVP
          </h1>
          <p className="text-zinc-400 text-sm">
            AI-Native Merchant Commerce Platform
          </p>
        </div>

        <div className="bg-black/50 rounded-lg p-6 flex flex-col gap-4 border border-zinc-800/50">
          {status === "loading" && (
            <div className="flex flex-col items-center gap-2">
              <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
              <p className="text-zinc-400">Connecting to Backend...</p>
            </div>
          )}

          {status === "connected" && (
            <>
              <div className="flex items-center justify-center gap-3 text-emerald-400 bg-emerald-400/10 px-4 py-2 rounded-full mb-2">
                <Activity className="w-5 h-5" />
                <span className="font-medium">🟢 Backend Status: Connected</span>
              </div>
              
              <div className="grid grid-cols-3 gap-2 mt-4 text-center">
                <div className="bg-zinc-800/50 rounded-lg p-3 flex flex-col items-center gap-2 border border-zinc-700/50">
                  <Store className="w-5 h-5 text-blue-400" />
                  <span className="text-2xl font-bold text-zinc-100">{stats.merchants}</span>
                  <span className="text-xs text-zinc-400">Merchants</span>
                </div>
                <div className="bg-zinc-800/50 rounded-lg p-3 flex flex-col items-center gap-2 border border-zinc-700/50">
                  <Package className="w-5 h-5 text-indigo-400" />
                  <span className="text-2xl font-bold text-zinc-100">{stats.products}</span>
                  <span className="text-xs text-zinc-400">Products</span>
                </div>
                <div className="bg-zinc-800/50 rounded-lg p-3 flex flex-col items-center gap-2 border border-zinc-700/50">
                  <Users className="w-5 h-5 text-purple-400" />
                  <span className="text-2xl font-bold text-zinc-100">{stats.customers}</span>
                  <span className="text-xs text-zinc-400">Customers</span>
                </div>
              </div>
            </>
          )}

          {status === "error" && (
            <div className="flex flex-col items-center gap-3 text-rose-400 bg-rose-400/10 px-4 py-3 rounded-xl text-center">
              <ServerCrash className="w-6 h-6" />
              <span className="font-medium">🔴 Backend Status: Disconnected</span>
              <p className="text-xs text-zinc-500">Ensure backend is running on port 8000 and database is seeded.</p>
            </div>
          )}
        </div>

        <div className="pt-4 flex justify-center">
          <Button 
            variant="outline" 
            className="w-full border-zinc-700 bg-zinc-800 text-zinc-200 hover:bg-zinc-700 hover:text-white transition-colors"
            onClick={() => window.location.reload()}
          >
            Refresh Status
          </Button>
        </div>
      </div>
    </div>
  );
}

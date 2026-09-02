"use client";

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/components/auth-provider';
import { ShieldCheck, Mail, Lock, ArrowRight, Loader2, Info } from 'lucide-react';
import { API_BASE } from '@/lib/api';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('password123'); // Pre-filled for demo convenience
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { login, user } = useAuth();
  const router = useRouter();

  // Routing is now driven by backend via redirect_url on successful login

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || 'Login failed');
      }
      
      login(data.access_token);
      if (data.redirect_url) {
        router.push(data.redirect_url);
      }
      
    } catch (err: any) {
      setError(err.message);
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 relative overflow-hidden">
      {/* Decorative background elements */}
      <div className="absolute top-0 left-0 w-full h-1/2 bg-[#02042b] clip-path-slant z-0"></div>
      
      <div className="relative z-10 w-full max-w-md p-6">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center p-3 bg-white/10 rounded-2xl backdrop-blur-md mb-4 border border-white/20">
            <ShieldCheck className="w-10 h-10 text-blue-400" />
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Agentic Commerce</h1>
          <p className="text-blue-200 mt-2">Unified Authentication Portal</p>
        </div>

        <div className="bg-white rounded-2xl shadow-xl border border-slate-100 overflow-hidden">
          <div className="p-8">
            <h2 className="text-xl font-semibold text-slate-800 mb-6">Sign in to your account</h2>
            
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-100 rounded-lg flex gap-3 text-red-700 text-sm">
                <AlertCircle className="w-5 h-5 shrink-0" />
                <p>{error}</p>
              </div>
            )}
            
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Email address</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Mail className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600 sm:text-sm transition-shadow outline-none"
                    placeholder="merchant@demo.local"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                    <Lock className="h-5 w-5 text-slate-400" />
                  </div>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="block w-full pl-10 pr-3 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-600 focus:border-blue-600 sm:text-sm transition-shadow outline-none"
                    placeholder="••••••••"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <input
                    id="remember-me"
                    name="remember-me"
                    type="checkbox"
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-slate-300 rounded"
                  />
                  <label htmlFor="remember-me" className="ml-2 block text-sm text-slate-600">
                    Remember me
                  </label>
                </div>

                <div className="text-sm">
                  <a href="#" className="font-medium text-blue-600 hover:text-blue-500">
                    Forgot password?
                  </a>
                </div>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full flex justify-center items-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-[#02042b] hover:bg-[#0a0f52] focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600 disabled:opacity-70 disabled:cursor-not-allowed transition-colors"
              >
                {isSubmitting ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    Sign in <ArrowRight className="ml-2 w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          </div>
          <div className="bg-slate-50 px-8 py-5 border-t border-slate-100">
            <div className="flex items-start gap-3">
              <Info className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
              <div className="text-xs text-slate-500 space-y-1.5">
                <p><strong>Demo Accounts (pwd: password123):</strong></p>
                <div className="flex flex-wrap gap-2">
                  <button onClick={() => setEmail('merchant@demo.local')} className="text-blue-600 hover:underline">TechNova Admin</button>
                  <button onClick={() => setEmail('amazon@demo.local')} className="text-blue-600 hover:underline">Amazon Demo Admin</button>
                  <button onClick={() => setEmail('flipkart@demo.local')} className="text-blue-600 hover:underline">Flipkart Demo Admin</button>
                  <button onClick={() => setEmail('customer@demo.local')} className="text-blue-600 hover:underline">Buyer / Customer</button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <p className="text-center text-sm text-slate-500 mt-8">
          By signing in, you agree to our Terms of Service and Privacy Policy.
        </p>
      </div>

      <style jsx>{`
        .clip-path-slant {
          clip-path: polygon(0 0, 100% 0, 100% 75%, 0 100%);
        }
      `}</style>
    </div>
  );
}

// Missing import for AlertCircle above, adding it here for standalone compilation if needed
import { AlertCircle } from 'lucide-react';

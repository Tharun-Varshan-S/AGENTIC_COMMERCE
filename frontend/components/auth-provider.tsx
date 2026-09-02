"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { API_BASE } from '@/lib/api';

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  merchant_id: string | null;
  merchant_name: string | null;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  login: () => {},
  logout: () => {},
  isLoading: true,
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const logout = () => {
    localStorage.removeItem('agentic_auth_token');
    setToken(null);
    setUser(null);
    router.push('/login');
  };

  const fetchUser = async (authToken: string) => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { 'Authorization': `Bearer ${authToken}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        throw new Error('Invalid token');
      }
    } catch (e) {
      console.error(e);
      logout();
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const storedToken = localStorage.getItem('agentic_auth_token');
    if (storedToken) {
      setToken(storedToken);
      fetchUser(storedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isLoading) return;
    
    const isProtected = pathname?.startsWith('/merchant') || pathname?.startsWith('/buyer');
    
    if (isProtected && !user && !token) {
      router.push('/login');
      return;
    }
    
    if (pathname?.startsWith('/merchant') && user && !user.role.startsWith('MERCHANT_') && user.role !== 'PLATFORM_ADMIN') {
      router.push('/buyer');
    }
  }, [pathname, user, token, isLoading, router]);

  const login = (newToken: string) => {
    localStorage.setItem('agentic_auth_token', newToken);
    setToken(newToken);
    setIsLoading(true);
    fetchUser(newToken).then(() => {
        // Redirection handled after fetching user role
    });
  };


  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

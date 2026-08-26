"use client";

import React, { createContext, useContext, useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';

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

  const fetchUser = async (authToken: string) => {
    try {
      const res = await fetch('http://localhost:8000/api/auth/me', {
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
    // Route protection logic
    if (isLoading) return;
    
    if (pathname?.startsWith('/merchant')) {
      if (!user) {
        router.push('/login');
      } else if (!user.role.startsWith('MERCHANT_')) {
        // Customer trying to access merchant area
        router.push('/buyer');
      }
    }
  }, [pathname, user, isLoading, router]);

  const login = (newToken: string) => {
    localStorage.setItem('agentic_auth_token', newToken);
    setToken(newToken);
    setIsLoading(true);
    fetchUser(newToken).then(() => {
        // Redirection handled after fetching user role
    });
  };

  const logout = () => {
    localStorage.removeItem('agentic_auth_token');
    setToken(null);
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  );
}

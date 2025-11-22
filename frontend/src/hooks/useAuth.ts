"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { authApi, setAccessToken, getAccessToken } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import type { User, AuthResponse } from "@/types";

interface UseAuthOptions {
  redirectTo?: string;
  redirectIfFound?: boolean;
}

export function useAuth(options: UseAuthOptions = {}) {
  const { redirectTo, redirectIfFound = false } = options;
  const router = useRouter();
  const { user, isAuthenticated, setUser, logout: storeLogout } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = getAccessToken();
      if (!token) {
        setIsLoading(false);
        if (redirectTo && !redirectIfFound) {
          router.push(redirectTo);
        }
        return;
      }

      try {
        const userData = await authApi.me();
        setUser(userData);
        if (redirectTo && redirectIfFound) {
          router.push(redirectTo);
        }
      } catch {
        setAccessToken(null);
        setUser(null);
        if (redirectTo && !redirectIfFound) {
          router.push(redirectTo);
        }
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [redirectTo, redirectIfFound, router, setUser]);

  const login = useCallback(
    async (email: string, password: string): Promise<AuthResponse> => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await authApi.login(email, password);
        const userData = await authApi.me();
        setUser(userData);
        return response;
      } catch (err: any) {
        const message = err.response?.data?.detail || "Error al iniciar sesion";
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [setUser]
  );

  const register = useCallback(
    async (email: string, password: string, name: string): Promise<AuthResponse> => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await authApi.register(email, password, name);
        const userData = await authApi.me();
        setUser(userData);
        return response;
      } catch (err: any) {
        const message = err.response?.data?.detail || "Error al registrarse";
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [setUser]
  );

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } finally {
      storeLogout();
      setIsLoading(false);
      router.push("/login");
    }
  }, [storeLogout, router]);

  const refreshToken = useCallback(async () => {
    try {
      await authApi.refresh();
    } catch {
      storeLogout();
      router.push("/login");
    }
  }, [storeLogout, router]);

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    refreshToken,
  };
}

// Hook for protected routes
export function useRequireAuth(redirectTo = "/login") {
  const { user, isLoading } = useAuth({ redirectTo });
  return { user, isLoading };
}

// Hook for public routes (redirect if already logged in)
export function useRedirectIfAuth(redirectTo = "/dashboard") {
  const { user, isLoading } = useAuth({ redirectTo, redirectIfFound: true });
  return { user, isLoading };
}

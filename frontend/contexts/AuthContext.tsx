"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, tokenStore } from "@/lib/api";
import type { TokenResponse, User } from "@/lib/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredTokens(): TokenResponse | null {
  const access = tokenStore.getAccess();
  const refresh = tokenStore.getRefresh();
  if (!access || !refresh) return null;
  return { access_token: access, refresh_token: refresh, token_type: "bearer" };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!tokenStore.getAccess()) {
      await Promise.resolve();
      setLoading(false);
      return;
    }
    try {
      const me = await api.me();
      setUser(me);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        tokenStore.clear();
        setUser(null);
      } else {
        setUser(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const tokens = readStoredTokens();
    if (!tokens) {
      void Promise.resolve().then(() => {
        if (!cancelled) setLoading(false);
      });
    } else {
      void api
        .me()
        .then((me) => {
          if (!cancelled) setUser(me);
        })
        .catch((err) => {
          if (cancelled) return;
          if (err instanceof ApiError && err.status === 401) tokenStore.clear();
          setUser(null);
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await api.login(email, password);
      tokenStore.setTokens(tokens.access_token, tokens.refresh_token);
      await refreshUser();
      router.push("/dashboard");
    },
    [refreshUser, router],
  );

  const register = useCallback(
    async (email: string, username: string, password: string) => {
      const tokens = await api.register(email, username, password);
      tokenStore.setTokens(tokens.access_token, tokens.refresh_token);
      await refreshUser();
      router.push("/dashboard");
    },
    [refreshUser, router],
  );

  const logout = useCallback(async () => {
    const refresh = tokenStore.getRefresh();
    const access = tokenStore.getAccess();
    tokenStore.clear();
    setUser(null);
    if (refresh) {
      try {
        await api.logout(refresh, access);
      } catch {
        /* ignore logout errors */
      }
    }
    router.push("/");
  }, [router]);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated: Boolean(user),
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { ENDPOINTS } from '@/constants/config';
// Use the centralised axios instance (has auto-refresh interceptor)
import api from '@/services/api';

// ── Types ──────────────────────────────────────────────────────────────────

// FIX (BUG-02): Add the full UserProfile type so profile fields are type-safe
// everywhere (index.tsx, profile.tsx etc.)
interface UserProfile {
  default_budget: number;
  default_travel_mode: string;
  interests_csv: string;
}

interface User {
  id: number;
  username: string;
  email: string;
  profile: UserProfile | null;  // FIX (BUG-02): was missing
}

interface AuthTokens {
  access: string;
  refresh: string;
}

interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  // FIX (BUG-01): expose setUser so ProfileScreen can update in-memory user
  // after a successful PUT /api/auth/me/ without needing an extra network round-trip.
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
  // refreshUser re-fetches /api/auth/me/ and syncs local state + AsyncStorage.
  // Use this when you want a guaranteed-fresh copy from the server.
  refreshUser: () => Promise<void>;
  login: (username: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (username: string, email: string, password: string, password2: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => Promise<void>;
}

// ── Storage keys ──────────────────────────────────────────────────────────
const TOKEN_KEY = '@travemle_tokens';
const USER_KEY  = '@travemle_user';

// ── Context ───────────────────────────────────────────────────────────────
const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser]       = useState<User | null>(null);
  const [tokens, setTokens]   = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // ── Load persisted auth on startup ──────────────────────────────────────
  useEffect(() => {
    const loadAuth = async () => {
      try {
        const [storedTokens, storedUser] = await Promise.all([
          AsyncStorage.getItem(TOKEN_KEY),
          AsyncStorage.getItem(USER_KEY),
        ]);
        if (storedTokens && storedUser) {
          const parsedTokens: AuthTokens = JSON.parse(storedTokens);
          const parsedUser: User         = JSON.parse(storedUser);
          setTokens(parsedTokens);
          setUser(parsedUser);
        }
      } catch (e) {
        console.error('Failed to load auth from storage:', e);
      } finally {
        setIsLoading(false);
      }
    };
    loadAuth();
  }, []);

  // ── Persist both user and tokens to AsyncStorage ──────────────────────
  const persistAuth = async (newUser: User, newTokens: AuthTokens) => {
    setUser(newUser);
    setTokens(newTokens);
    await Promise.all([
      AsyncStorage.setItem(TOKEN_KEY, JSON.stringify(newTokens)),
      AsyncStorage.setItem(USER_KEY,  JSON.stringify(newUser)),
    ]);
  };

  // ── Login ─────────────────────────────────────────────────────────────
  const login = async (username: string, password: string) => {
    try {
      // Use raw ENDPOINTS.login — auth endpoints don't need the interceptor's token header
      const res = await api.post(ENDPOINTS.login, { username, password });
      await persistAuth(res.data.user, res.data.tokens);
      return { success: true };
    } catch (err: any) {
      const error = err?.response?.data?.error || err?.response?.data?.detail || 'Login failed. Please try again.';
      return { success: false, error };
    }
  };

  // ── Register ──────────────────────────────────────────────────────────
  const register = async (
    username: string,
    email: string,
    password: string,
    password2: string,
  ) => {
    try {
      const res = await api.post(ENDPOINTS.register, { username, email, password, password2 });
      await persistAuth(res.data.user, res.data.tokens);
      return { success: true };
    } catch (err: any) {
      const errData = err?.response?.data;
      const error =
        errData?.username?.[0] ||
        errData?.email?.[0]    ||
        errData?.password?.[0] ||
        errData?.error         ||
        'Registration failed. Please try again.';
      return { success: false, error };
    }
  };

  // ── Refresh user from server ─────────────────────────────────────────
  // FIX (BUG-01): Call this after a profile update to get the latest
  // server-side user data (including updated profile fields) and persist
  // it so AsyncStorage stays in sync.
  const refreshUser = async () => {
    try {
      const res = await api.get(ENDPOINTS.me);
      const freshUser: User = res.data;
      setUser(freshUser);
      await AsyncStorage.setItem(USER_KEY, JSON.stringify(freshUser));
    } catch (e) {
      console.error('Failed to refresh user:', e);
    }
  };

  // ── Logout ────────────────────────────────────────────────────────────
  const logout = async () => {
    // Clear local state immediately so the guard redirects to login
    setUser(null);
    setTokens(null);
    await Promise.all([
      AsyncStorage.removeItem(TOKEN_KEY),
      AsyncStorage.removeItem(USER_KEY),
    ]);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        tokens,
        isLoading,
        isAuthenticated: !!user && !!tokens,
        setUser,       // FIX (BUG-01): exposed for direct local state updates
        refreshUser,   // FIX (BUG-01): exposed for server-synced updates
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

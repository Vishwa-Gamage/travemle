/**
 * services/api.ts
 * ─────────────────────────────────────────────────────────────
 * Centralised axios instance with automatic JWT token refresh.
 *
 * HOW IT WORKS:
 *  1. Every request automatically gets the stored access token.
 *  2. If a 401 is returned, it tries to refresh using the stored
 *     refresh token via POST /api/auth/refresh/.
 *  3. If refresh succeeds, it retries the original request once.
 *  4. If refresh fails (token expired / invalid), it clears
 *     storage so the auth guard redirects to login.
 * ─────────────────────────────────────────────────────────────
 */

import axios, { AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL, ENDPOINTS } from '@/constants/config';

// ── Storage keys (must match AuthContext) ───────────────────
const TOKEN_KEY = '@travemle_tokens';
const USER_KEY  = '@travemle_user';

// ── Create base instance ─────────────────────────────────────
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 s — AI endpoint can be slow
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor — attach access token ────────────────
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      const raw = await AsyncStorage.getItem(TOKEN_KEY);
      if (raw) {
        const tokens = JSON.parse(raw);
        if (tokens?.access) {
          config.headers = config.headers ?? {};
          config.headers['Authorization'] = `Bearer ${tokens.access}`;
        }
      }
    } catch {
      // If storage read fails, continue without token
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ── Track whether we are already refreshing to avoid loops ──
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: any) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((p) => {
    if (error) {
      p.reject(error);
    } else {
      p.resolve(token);
    }
  });
  failedQueue = [];
};

// ── Response interceptor — handle 401 with refresh ──────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    // Only attempt refresh on 401 and only once per request
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Queue this request until the refresh completes
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              (originalRequest.headers as any)['Authorization'] = `Bearer ${token}`;
            }
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const raw = await AsyncStorage.getItem(TOKEN_KEY);
        if (!raw) throw new Error('No tokens stored');

        const tokens = JSON.parse(raw);
        if (!tokens?.refresh) throw new Error('No refresh token');

        // Call the refresh endpoint directly (without our interceptor to avoid loop)
        const res = await axios.post(ENDPOINTS.refresh, { refresh: tokens.refresh });
        const newAccessToken: string = res.data.access;
        // SimpleJWT may also rotate the refresh token
        const newRefreshToken: string = res.data.refresh ?? tokens.refresh;

        // Persist updated tokens
        const updatedTokens = { access: newAccessToken, refresh: newRefreshToken };
        await AsyncStorage.setItem(TOKEN_KEY, JSON.stringify(updatedTokens));

        // Update default header for future requests
        api.defaults.headers.common['Authorization'] = `Bearer ${newAccessToken}`;

        processQueue(null, newAccessToken);

        // Retry the original request with the new token
        if (originalRequest.headers) {
          (originalRequest.headers as any)['Authorization'] = `Bearer ${newAccessToken}`;
        }
        return api(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError, null);

        // Refresh failed — clear auth state so guard redirects to login
        await Promise.all([
          AsyncStorage.removeItem(TOKEN_KEY),
          AsyncStorage.removeItem(USER_KEY),
        ]);

        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

export default api;

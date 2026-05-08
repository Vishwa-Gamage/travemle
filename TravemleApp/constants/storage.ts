/**
 * constants/storage.ts
 * ─────────────────────────────────────────────────────────────
 * Single source of truth for AsyncStorage keys to prevent typos
 * across api.ts and AuthContext.tsx.
 * ─────────────────────────────────────────────────────────────
 */

export const STORAGE_KEYS = {
  TOKENS: '@travemle_tokens',
  USER: '@travemle_user',
};

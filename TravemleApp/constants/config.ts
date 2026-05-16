/**
 * constants/config.ts
 * ─────────────────────────────────────────────────────────────
 * Central API configuration.
 *
 * HOW TO CHANGE THE SERVER IP:
 *  • Android device / Expo Go: use your machine's LAN IP
 *    e.g.  'http://192.168.1.42:8000'
 *  • Android Emulator:         'http://10.0.2.2:8000'
 *  • iOS Simulator:            'http://localhost:8000'
 *  • Web (same machine):       'http://localhost:8000'
 * ─────────────────────────────────────────────────────────────
 */

import { Platform } from 'react-native';

export const API_BASE_URL = Platform.OS === 'web' 
  ? 'http://localhost:8000' 
  : 'http://192.168.1.80:8000';

export const ENDPOINTS = {
  // Auth
  register:           `${API_BASE_URL}/api/auth/register/`,
  login:              `${API_BASE_URL}/api/auth/login/`,
  logout:             `${API_BASE_URL}/api/auth/logout/`,
  refresh:            `${API_BASE_URL}/api/auth/refresh/`,
  me:                 `${API_BASE_URL}/api/auth/me/`,

  // Planner
  planTrip:           `${API_BASE_URL}/api/plan-trip/`,
  destinations:       `${API_BASE_URL}/api/destinations/`,

  // Trip history — list/create and detail (for delete)
  tripHistory:        `${API_BASE_URL}/api/trip-history/`,
  tripHistoryDetail:  (id: number) => `${API_BASE_URL}/api/trip-history/${id}/`,
  
  // Chatbot
  chat:               `${API_BASE_URL}/api/chat/`,

  // User behaviour insights (auto-analyzed from trip history)
  insights:           `${API_BASE_URL}/api/insights/`,
};

/**
 * constants/interests.ts
 * ─────────────────────────────────────────────────────────────
 * Single source of truth for interest categories used across:
 *  - app/(tabs)/index.tsx   (Plan screen trip form)
 *  - app/(tabs)/profile.tsx (Profile preferences)
 *  - planner/models.py      (Destination.CATEGORY_CHOICES)
 *
 * FIX (BUG-04): Previously index.tsx had 6 interests and profile.tsx had 8.
 * "History" and "Wildlife" set in Profile were silently lost in Plan screen.
 * ─────────────────────────────────────────────────────────────
 */

export const INTERESTS = [
  'Nature',
  'Culture',
  'Temple',
  'Beach',
  'Adventure',
  'Food',
  'History',    // was missing from index.tsx
  'Wildlife',   // was missing from index.tsx
] as const;

export type Interest = typeof INTERESTS[number];

// ── Mihiran's preference constants (feature/preferences) ─────────────────────

export const FOOD_PREFERENCES = [
  'Spicy',
  'Vegan',
  'Vegetarian',
  'Seafood',
  'Local Cuisine',
  'Fast Food',
  'Halal',
] as const;

export const ACCOMMODATION_PREFERENCES = [
  'Hotel',
  'Hostel',
  'Villa',
  'Resort',
  'Homestay',
  'Guest House',
] as const;

export const ACTIVITY_PREFERENCES = [
  'Hiking',
  'Surfing',
  'Relaxing',
  'Sightseeing',
  'Shopping',
  'Nightlife',
] as const;

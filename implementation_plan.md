# Travemle Project Analysis and Implementation Plan

This document provides a full analysis of the current Travemle project against the submitted "Final Year Project Proposal" and outlines a clear plan to fulfill the missing objectives.

## Analysis of Current State vs Proposal

| Proposal Objective | Current Implementation Status | What is Missing |
| --- | --- | --- |
| **1. User Profile & Preferences** | 🟡 Partial | The frontend passes constraints per-request, but there is no persistent `UserProfile` model in Django tracking long-term interests, historical travel patterns, and default constraints. |
| **2. ML Recommendation Models** | 🟡 Partial | Uses LLM (LLaMA via Groq) to generate itineraries. However, it lacks a dedicated recommendation endpoint filtering `Destination` models based on the user profile prior to LLM generation. |
| **3. Optimization Techniques** | 🟡 Partial | Heavily reliant on LLM prompting. Needs explicit pre-filtering or algorithmic optimization logic (e.g., scoring destinations based on distance/budget constraints) to "maximize customer happiness while reducing travel expenses and time". |
| **4. Architecture (Django + React)** | 🟢 Completed | Solid Django REST backend + Expo React Native frontend with JWT Auth. |
| **5. Real-Time Data (Weather/Traffic)** | 🟢 Completed | OpenWeather API is integrated effectively. Google Maps URLs are generated for routing. |

---

## User Review Required

> [!IMPORTANT]
> The proposal mentions using "PostgreSQL/MongoDB". The project currently uses SQLite. Since SQLite is perfect for local development and testing, I propose we stick to SQLite for now and handle the PostgreSQL migration during final deployment. Are you okay with keeping SQLite for the current development phase?

## Proposed Changes

We will implement the missing functionality by updating the backend `planner` app and the frontend `TravemleApp`.

### Backend: `planner` app

#### [MODIFY] `planner/models.py`
- Add a new `UserProfile` model linked one-to-one with the `User` model.
- Fields: `default_budget`, `default_travel_mode`, `interests_csv`, `preferred_trip_length`.
- Update signals to automatically create a `UserProfile` when a `User` registers.

#### [MODIFY] `planner/serializers.py`
- Add `UserProfileSerializer`.
- Update `UserSerializer` to nest the `UserProfile` data.

#### [MODIFY] `planner/views.py`
- Update `MeView` and `RegisterView` to handle `UserProfile` creation and updates.
- Create a new `RecommendationEngine` function that takes a `UserProfile` and `TripPlan` history, applying algorithmic scoring to the `Destination` database based on matching `category` and user `interests`.
- Modify `TravelPlanView` so that before calling the LLM, it uses the algorithmic scoring to filter the top 5 appropriate destinations to include in the LLM context, acting as a hybrid ML/Optimization pipeline.

---

### Frontend: `TravemleApp`

#### [NEW] `app/(tabs)/profile.tsx`
- Create a new Profile tab to allow users to permanently save their `interests`, `default_budget`, and `default_travel_mode`.
- This ensures the UI reflects Objective 1 of your proposal ("thorough user profile").

#### [MODIFY] `app/(tabs)/_layout.tsx`
- Add the new `profile` screen to the bottom tab bar.

#### [MODIFY] `app/(tabs)/index.tsx`
- Refactor the state initialization to fetch the user's default preferences from the new `UserProfile` backend data.

## Verification Plan

### Automated Tests
- Run `python manage.py makemigrations` and `python manage.py migrate` to ensure the DB structure updates successfully.
- Verify user profile updates via API calls.

### Manual Verification
- Log into the Expo app, navigate to the new Profile tab, and save travel preferences.
- Navigate to the Plan tab and ensure the default values auto-populate correctly.
- Generate a trip and verify that the backend logs show the algorithmic filtering working prior to LLM generation.

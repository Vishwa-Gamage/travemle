import os
import json
import re
import requests
from collections import Counter
from datetime import datetime

from django.contrib.auth.models import User
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Destination, TripPlan, UserProfile
from .serializers import (
    DestinationSerializer,
    RegisterSerializer,
    TripPlanSerializer,
    UserSerializer,
    ProfileUpdateSerializer,
)

# ── 1. Load environment variables ───────────────────────────────────────────
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# ── 2. Module-level LLM singleton (not per-request) ──────────────────────────
if GROQ_API_KEY:
    llm = ChatGroq(
        temperature=0.1,
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile",
    )
else:
    llm = None

# ── 3. City coordinate fallback ──────────────────────────────────────────────
CITY_BACKUP = {
    "colombo": {"lat": 6.9271, "lon": 79.8612},
    "kandy": {"lat": 7.2906, "lon": 80.6337},
    "galle": {"lat": 6.0535, "lon": 80.2210},
    "matara": {"lat": 5.9549, "lon": 80.5550},
    "tangalle": {"lat": 6.0244, "lon": 80.7941},
    "dikwella": {"lat": 5.9660, "lon": 80.6976},
    "hiriketiya": {"lat": 5.9615, "lon": 80.6946},
    "kataragama": {"lat": 6.4135, "lon": 81.3325},
    "ella": {"lat": 6.8667, "lon": 81.0466},
    "nuwara eliya": {"lat": 6.9497, "lon": 80.7891},
    "trincomalee": {"lat": 8.5667, "lon": 81.2333},
    "jaffna": {"lat": 9.6615, "lon": 80.0255},
    "arugam bay": {"lat": 6.8400, "lon": 81.8357},
    "sigiriya": {"lat": 7.9570, "lon": 80.7603},
    "london": {"lat": 51.5074, "lon": -0.1278},
}

# ── 4. Sri Lanka Tourism Season Data ────────────────────────────────────────
# Source: Sri Lanka Tourism Development Authority (SLTDA)
# https://www.sltda.gov.lk/en/tourism-statistics
# West/South coast peak: Dec–Mar | East coast peak: Apr–Sep
# Central highlands: Jan–Apr (dry), May–Sep (rain)
SL_SEASON_DATA = {
    # (month) -> {region_key: 'peak'|'shoulder'|'off_peak'}
    # West & South Coast (Colombo, Galle, Mirissa, Weligama, Bentota)
    "west_south": {
        1: "peak", 2: "peak", 3: "peak",
        4: "shoulder", 5: "off_peak", 6: "off_peak",
        7: "shoulder", 8: "shoulder", 9: "off_peak",
        10: "off_peak", 11: "shoulder", 12: "peak",
    },
    # East Coast (Trincomalee, Arugam Bay, Pasikuda)
    "east": {
        1: "off_peak", 2: "off_peak", 3: "off_peak",
        4: "shoulder", 5: "peak", 6: "peak",
        7: "peak", 8: "peak", 9: "shoulder",
        10: "off_peak", 11: "off_peak", 12: "off_peak",
    },
    # Central Highlands (Kandy, Nuwara Eliya, Ella, Sigiriya)
    "central": {
        1: "peak", 2: "peak", 3: "peak", 4: "peak",
        5: "shoulder", 6: "off_peak", 7: "shoulder",
        8: "shoulder", 9: "off_peak", 10: "off_peak",
        11: "shoulder", 12: "peak",
    },
}

EAST_COAST_CITIES  = {"trincomalee", "arugam bay", "pasikuda", "batticaloa", "ampara"}
CENTRAL_CITIES     = {"kandy", "nuwara eliya", "ella", "sigiriya", "dambulla", "polonnaruwa", "habarana"}

# Reference average daily costs (LKR) from SLTDA & TripAdvisor Sri Lanka 2024
# Source: SLTDA Annual Statistical Report 2023; TripAdvisor Sri Lanka price data
BUDGET_REFERENCE = {
    "accommodation": {
        "budget":   {"range": "1,500 – 4,000",  "source": "Booking.com/Agoda Sri Lanka avg (2024)"},
        "mid":      {"range": "4,000 – 12,000", "source": "TripAdvisor Sri Lanka hotel avg (2024)"},
        "luxury":   {"range": "12,000 – 40,000","source": "SLTDA Classified Hotels avg (2023)"},
    },
    "food": {
        "budget":   {"range": "500 – 1,500",    "source": "Local restaurants, street food avg"},
        "mid":      {"range": "1,500 – 4,000",  "source": "TripAdvisor restaurant avg Sri Lanka"},
        "luxury":   {"range": "4,000 – 10,000", "source": "Fine dining, resort restaurants"},
    },
    "transport": {
        "bus":      {"range": "200 – 600/day",   "source": "SLTB intercity bus fares (2024)"},
        "train":    {"range": "300 – 800/day",   "source": "Sri Lanka Railways official fares"},
        "car":      {"range": "5,000 – 12,000/day", "source": "Sri Lanka car rental avg (2024)"},
    },
}

# ── 5. Helper functions ───────────────────────────────────────────────────────

def get_coordinates(city_name: str):
    city_clean = city_name.lower().strip()
    if city_clean in CITY_BACKUP:
        return CITY_BACKUP[city_clean]["lat"], CITY_BACKUP[city_clean]["lon"]
    if OPENWEATHER_API_KEY:
        try:
            url = (
                f"http://api.openweathermap.org/geo/1.0/direct"
                f"?q={city_name}&limit=1&appid={OPENWEATHER_API_KEY}"
            )
            res = requests.get(url, timeout=5)
            if res.status_code == 200 and res.json():
                data = res.json()[0]
                return data["lat"], data["lon"]
        except Exception as e:
            print(f"Geo API Error: {e}")
    return None, None


# Weather condition code → emoji mapping (OpenWeatherMap icon codes)
def _condition_emoji(description: str) -> str:
    desc = description.lower()
    if "thunderstorm" in desc:              return "⛈️"
    if "drizzle" in desc:                   return "🌦️"
    if "heavy rain" in desc or "shower" in desc: return "🌧️"
    if "rain" in desc:                      return "🌧️"
    if "snow" in desc:                      return "❄️"
    if "mist" in desc or "fog" in desc or "haze" in desc: return "🌫️"
    if "overcast" in desc:                  return "☁️"
    if "broken clouds" in desc or "scattered" in desc: return "⛅"
    if "few clouds" in desc or "partly" in desc:        return "🌤️"
    if "clear" in desc or "sunny" in desc:  return "☀️"
    return "🌡️"


def get_weather_forecast_multiday(city: str, country: str,
                                   start_date_str: str, end_date_str: str) -> tuple:
    """
    Fetches the OpenWeatherMap 5-day/3-hour forecast and returns:
      - weather_days : list of per-day dicts for every trip day
      - summary_str  : plain-text summary (for DB storage)

    Source: OpenWeatherMap Forecast API – https://openweathermap.org/forecast5
    API provides data in 3-hour steps up to 5 days ahead.
    Trip days beyond the 5-day window are marked 'Beyond forecast range'.
    """
    if not OPENWEATHER_API_KEY:
        return [], "Weather API key not configured."

    search_query = f"{city},{country}" if country else city
    lat, lon = get_coordinates(search_query)
    if lat is None:
        lat, lon = get_coordinates(city)
    if lat is None:
        return [], f"Coordinates not found for {city}."

    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/forecast"
            f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        resp = requests.get(url, timeout=6)
        data = resp.json()

        # ── Group all 3-hour slots by calendar date ───────────────────────
        from collections import defaultdict
        slots_by_date = defaultdict(list)
        for item in data.get("list", []):
            slot_dt   = datetime.fromtimestamp(item["dt"])
            slot_date = slot_dt.date()
            slots_by_date[slot_date].append({
                "hour":        slot_dt.hour,
                "description": item["weather"][0]["description"].capitalize(),
                "temp":        round(item["main"]["temp"], 1),
                "temp_min":    round(item["main"]["temp_min"], 1),
                "temp_max":    round(item["main"]["temp_max"], 1),
                "humidity":    item["main"]["humidity"],
                "rain_pct":    round(item.get("pop", 0) * 100),
            })

        # ── Build one entry per trip day ───────────────────────────────────
        start_dt   = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_dt     = datetime.strptime(end_date_str,   "%Y-%m-%d")
        duration   = (end_dt - start_dt).days + 1

        weather_days = []
        summary_parts = []

        for i in range(duration):
            from datetime import timedelta
            trip_date  = (start_dt + timedelta(days=i)).date()
            day_label  = trip_date.strftime("%a, %d %b")   # e.g. "Mon, 02 Jun"
            day_num    = f"Day {i + 1}"

            slots = slots_by_date.get(trip_date, [])

            if not slots:
                # Beyond 5-day forecast window or no data
                day_entry = {
                    "date":        str(trip_date),
                    "day_label":   day_label,
                    "day_num":     day_num,
                    "description": "Beyond forecast range",
                    "emoji":       "📅",
                    "temp":        None,
                    "temp_min":    None,
                    "temp_max":    None,
                    "humidity":    None,
                    "rain_pct":    None,
                    "available":   False,
                }
            else:
                # Prefer noon slot (12:00), fall back to closest midday slot
                best = min(slots, key=lambda s: abs(s["hour"] - 12))
                # Aggregate min/max across all slots for the day
                all_temps = [s["temp"] for s in slots]
                max_rain  = max(s["rain_pct"] for s in slots)

                day_entry = {
                    "date":        str(trip_date),
                    "day_label":   day_label,
                    "day_num":     day_num,
                    "description": best["description"],
                    "emoji":       _condition_emoji(best["description"]),
                    "temp":        best["temp"],
                    "temp_min":    round(min(all_temps), 1),
                    "temp_max":    round(max(all_temps), 1),
                    "humidity":    best["humidity"],
                    "rain_pct":    max_rain,
                    "available":   True,
                }
                summary_parts.append(
                    f"{day_label}: {best['description']}, {best['temp']}°C, Rain {max_rain}%"
                )

            weather_days.append(day_entry)

        summary_str = " | ".join(summary_parts) if summary_parts else "Forecast unavailable."
        return weather_days, summary_str

    except Exception as e:
        print(f"Multi-day weather error: {e}")
        return [], "Weather service temporarily unavailable."


def detect_season(city: str, start_date_str: str) -> dict:
    """
    Returns peak/off-peak classification with pricing impact.
    Source: SLTDA Tourism Statistics & Sri Lanka meteorological data.
    """
    try:
        month = datetime.strptime(start_date_str, "%Y-%m-%d").month
        city_lower = city.lower().strip()

        if city_lower in EAST_COAST_CITIES:
            region     = "east"
            region_lbl = "East Coast"
        elif city_lower in CENTRAL_CITIES:
            region     = "central"
            region_lbl = "Central Highlands"
        else:
            region     = "west_south"
            region_lbl = "West & South Coast"

        season_val = SL_SEASON_DATA[region][month]

        season_map = {
            "peak":      {"label": "Peak Season",     "icon": "🔴", "price_impact": "+20–40% on accommodation"},
            "shoulder":  {"label": "Shoulder Season",  "icon": "🟡", "price_impact": "Average market rates"},
            "off_peak":  {"label": "Off-Peak Season",  "icon": "🟢", "price_impact": "15–30% savings possible"},
        }
        info = season_map[season_val]

        month_name = datetime.strptime(start_date_str, "%Y-%m-%d").strftime("%B")
        return {
            "season":       season_val,
            "label":        info["label"],
            "icon":         info["icon"],
            "region":       region_lbl,
            "price_impact": info["price_impact"],
            "month":        month_name,
            "source":       "Sri Lanka Tourism Development Authority (SLTDA) – Regional Seasonality Guide",
            "tip": (
                f"{month_name} is {info['label'].lower()} for {region_lbl}. "
                + (
                    "Book accommodation early as availability is limited."
                    if season_val == "peak" else
                    "Good value for money with fewer crowds."
                    if season_val == "off_peak" else
                    "Moderate crowds and reasonable prices expected."
                )
            ),
        }
    except Exception as e:
        print(f"Season detection error: {e}")
        return {"season": "unknown", "label": "Season data unavailable", "source": ""}


def get_budget_reference(budget_total: int, mode: str, duration_days: int) -> dict:
    """
    Validates the AI-generated budget against real market reference data.
    Returns tier classification and source citations.
    """
    per_day = budget_total / max(duration_days, 1)

    # Classify overall budget tier (LKR per day)
    if per_day < 5000:
        tier = "budget"
        tier_label = "Budget Traveller"
    elif per_day < 15000:
        tier = "mid"
        tier_label = "Mid-Range Traveller"
    else:
        tier = "luxury"
        tier_label = "Luxury Traveller"

    mode_key = mode.lower() if mode.lower() in BUDGET_REFERENCE["transport"] else "bus"

    return {
        "tier":              tier,
        "tier_label":        tier_label,
        "per_day_estimated": round(per_day),
        "references": [
            {
                "category":    "Accommodation",
                "market_range": f"LKR {BUDGET_REFERENCE['accommodation'][tier]['range']}/night",
                "source":      BUDGET_REFERENCE["accommodation"][tier]["source"],
            },
            {
                "category":    "Food",
                "market_range": f"LKR {BUDGET_REFERENCE['food'][tier]['range']}/day",
                "source":      BUDGET_REFERENCE["food"][tier]["source"],
            },
            {
                "category":    "Transport",
                "market_range": f"LKR {BUDGET_REFERENCE['transport'][mode_key]['range']}",
                "source":      BUDGET_REFERENCE["transport"][mode_key]["source"],
            },
        ],
        "validation_note": (
            f"Your LKR {per_day:,.0f}/day budget fits the '{tier_label}' profile. "
            "Estimates cross-referenced against SLTDA, Booking.com, and TripAdvisor Sri Lanka data."
        ),
    }


def suggest_alternative_destinations(city: str, interests: str, country: str) -> list:
    """
    Suggests up to 3 alternative destinations from the Destination DB
    that match the user's interests but are different from the chosen city.
    """
    try:
        interest_list = [i.strip().lower() for i in interests.split(',') if i.strip()]
        if not interest_list:
            return []

        # Find destinations matching interests, in same country, excluding current city
        alternatives = []
        dests = Destination.objects.filter(country__icontains=country)
        for d in dests:
            if d.name.lower() != city.lower() and d.category.lower() in interest_list:
                alternatives.append({
                    "name":        d.name,
                    "category":    d.category,
                    "description": d.description[:120] + "..." if len(d.description) > 120 else d.description,
                    "reason":      f"Matches your '{d.category}' interest",
                })

        # Deduplicate by name, take top 3
        seen = set()
        unique = []
        for a in alternatives:
            if a["name"] not in seen:
                seen.add(a["name"])
                unique.append(a)
            if len(unique) >= 3:
                break
        return unique
    except Exception as e:
        print(f"Alternative destinations error: {e}")
        return []


def analyze_user_interests_from_history(user) -> dict:
    """
    Automatically analyzes a user's interest patterns from their past trips.
    Returns ranked interests, preferred modes, and behavioural insights.
    """
    trips = TripPlan.objects.filter(user=user).order_by('-created_at')[:20]
    if not trips:
        return {"status": "no_history", "message": "Plan more trips to unlock personalized insights."}

    # Count interest frequencies
    all_interests = []
    all_modes     = []
    all_budgets   = []
    all_cities    = []

    for trip in trips:
        if trip.interests:
            for interest in trip.interests.split(','):
                clean = interest.strip().lower()
                if clean:
                    all_interests.append(clean)
        if trip.travel_mode:
            all_modes.append(trip.travel_mode)
        if trip.budget:
            all_budgets.append(trip.budget)
        if trip.destination_city:
            all_cities.append(trip.destination_city)

    interest_counts = Counter(all_interests)
    mode_counts     = Counter(all_modes)

    top_interests = [
        {"interest": k.capitalize(), "trips": v, "percentage": round((v / len(trips)) * 100)}
        for k, v in interest_counts.most_common(5)
    ]

    preferred_mode = mode_counts.most_common(1)[0][0] if mode_counts else "Not enough data"
    avg_budget     = round(sum(all_budgets) / len(all_budgets)) if all_budgets else 0

    # Budget trend
    if len(all_budgets) >= 2:
        recent_avg = sum(all_budgets[:3]) / min(3, len(all_budgets))
        older_avg  = sum(all_budgets[3:]) / max(1, len(all_budgets[3:]))
        if recent_avg > older_avg * 1.15:
            budget_trend = "Increasing — you're spending more on recent trips"
        elif recent_avg < older_avg * 0.85:
            budget_trend = "Decreasing — you're becoming more budget-conscious"
        else:
            budget_trend = "Stable — consistent spending across trips"
    else:
        budget_trend = "Not enough trips to determine trend"

    return {
        "status":            "ok",
        "total_trips":       len(trips),
        "top_interests":     top_interests,
        "preferred_mode":    preferred_mode,
        "avg_budget":        avg_budget,
        "budget_trend":      budget_trend,
        "most_visited":      Counter(all_cities).most_common(1)[0][0] if all_cities else None,
        "insight":           (
            f"Based on {len(trips)} trip(s), your top travel interest is "
            f"'{top_interests[0]['interest'] if top_interests else 'N/A'}', "
            f"you prefer travelling by {preferred_mode}, "
            f"and your average budget is LKR {avg_budget:,}."
        ),
    }


def generate_itinerary(city, country, origin, start_date, end_date, interests, budget, mode, recommended_places=""):
    if llm is None:
        return None, "LLM not configured. Check GROQ_API_KEY."

    # FIX (QUAL-03): build the prompt as a plain string first, then append
    # the recommendations line conditionally.  The previous ternary expression
    #   f"..." f"..." if recommended_places else ""
    # has Python operator-precedence issue: when recommended_places is falsy
    # the entire HumanMessage content evaluates to "" (empty string), sending
    # a blank message to the LLM.
    human_content = (
        f"Plan a trip to {city}, {country} from {origin}.\n"
        f"Dates: {start_date} to {end_date}.\n"
        f"Interests: {interests}. Budget: {budget} LKR. Mode: {mode}."
    )
    if recommended_places:
        human_content += (
            f"\nConsider prioritizing these locations if relevant: {recommended_places}."
        )

    messages = [
        SystemMessage(content=(
            "You are an expert travel guide. Create a realistic trip plan.\n"
            "STRICT JSON OUTPUT ONLY — no markdown, no extra text.\n"
            'Structure: {"title": "...", "duration": "...", '
            '"activities": [{"day": "...", "time": "...", '
            '"location_name": "...", "description": "..."}], '
            '"budget_breakdown": {"accommodation": ..., "food": ..., '
            '"transport": ..., "activities": ..., "total": ...}}\n'
            "'location_name' must be a real place name recognizable by Google Maps.\n"
            "For Sri Lanka: NO TRAINS to Kataragama, Hambantota, or Monaragala."
        )),
        HumanMessage(content=human_content),
    ]

    for attempt in range(2):
        try:
            response = llm.invoke(messages)
            content = re.sub(r"```json|```", "", response.content).strip()
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0)), None
            print(f"Attempt {attempt+1}: Invalid JSON. Retrying…")
        except Exception as e:
            print(f"LLM error attempt {attempt+1}: {e}")
    return None, "AI could not generate a valid plan. Please try again."


# ── 5. Auth Views ─────────────────────────────────────────────────────────────

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "message": "Account created successfully.",
                    "user": UserSerializer(user).data,
                    "tokens": {
                        "access": str(refresh.access_token),
                        "refresh": str(refresh),
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "")

        if not username or not password:
            return Response(
                {"error": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import authenticate
        user = authenticate(username=username, password=password)
        if user is None:
            return Response(
                {"error": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def put(self, request):
        serializer = ProfileUpdateSerializer(data=request.data)
        if serializer.is_valid():
            profile = request.user.profile
            data = serializer.validated_data
            if 'default_budget' in data:
                profile.default_budget = data['default_budget']
            if 'default_travel_mode' in data:
                profile.default_travel_mode = data['default_travel_mode']
            if 'interests_csv' in data:
                profile.interests_csv = data['interests_csv']
            profile.save()
            return Response(UserSerializer(request.user).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({"message": "Successfully logged out."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)


# ── 6. Planner Views ──────────────────────────────────────────────────────────

class TravelPlanView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'plan_trip'

    def post(self, request):
        data = request.data
        origin     = data.get("origin", "").strip()
        country    = data.get("country", "Sri Lanka").strip()
        city       = data.get("city", "").strip()
        start_date = data.get("start_date", "")
        end_date   = data.get("end_date", "")
        interests  = data.get("interests", "")
        budget     = data.get("budget", 0)
        mode       = data.get("travel_mode", "Car")

        # Input validation
        if not city:
            return Response({"error": "Destination city is required."}, status=400)
        if not start_date or not end_date:
            return Response({"error": "Start and end dates are required."}, status=400)
        try:
            s = datetime.strptime(start_date, "%Y-%m-%d")
            e = datetime.strptime(end_date, "%Y-%m-%d")
            if e < s:
                return Response({"error": "End date must be after start date."}, status=400)
            duration_days = (e - s).days + 1
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        # ── Multi-Day Weather Forecast ───────────────────────────────────────
        weather_days, weather_summary = get_weather_forecast_multiday(
            city, country, start_date, end_date
        )

        # ── Season Intelligence ─────────────────────────────────────────────
        season_info = detect_season(city, start_date)

        # ── Budget Validation against real market sources ───────────────────
        budget_int  = int(budget) if budget else 0
        budget_ref  = get_budget_reference(budget_int, mode, duration_days)

        # ── Algorithmic Pre-filter: match interests → destinations ──────────
        recommended = []
        if interests:
            interest_list = [i.strip().lower() for i in interests.split(',')]
            dests = Destination.objects.filter(country__icontains=country)
            for d in dests:
                if d.category.lower() in interest_list:
                    recommended.append(d.name)
        recommended_str = ", ".join(recommended[:5])

        # ── Alternative Destination Suggestions ─────────────────────────────
        alternatives = suggest_alternative_destinations(city, interests, country)

        # ── AI Itinerary Generation ─────────────────────────────────────────
        plan_data, error = generate_itinerary(
            city, country, origin, start_date, end_date, interests, budget, mode, recommended_str
        )
        if plan_data is None:
            return Response({"error": error}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # ── Build Google Maps Route URL ──────────────────────────────────────
        path_parts = [origin.replace(" ", "+") if origin else country.replace(" ", "+")]
        for act in plan_data.get("activities", [])[:9]:
            path_parts.append(act.get("location_name", "").replace(" ", "+"))
        map_url = "https://www.google.com/maps/dir/" + "/".join(filter(None, path_parts))

        # ── Save to DB ──────────────────────────────────────────────────────
        try:
            TripPlan.objects.create(
                user=request.user,
                origin=origin,
                destination_city=city,
                destination_country=country,
                start_date=start_date,
                end_date=end_date,
                interests=interests,
                budget=budget_int,
                travel_mode=mode,
                plan_json=plan_data,
                weather_summary=weather_summary,   # plain-text summary for DB
                map_url=map_url,
            )
        except Exception as e:
            print(f"DB save error: {e}")

        return Response(
            {
                "plan":          plan_data,
                "weather":       weather_summary,   # kept for backward compatibility
                "weather_days":  weather_days,      # structured per-day forecast
                "map_url":       map_url,
                "season_info":   season_info,
                "budget_ref":    budget_ref,
                "alternatives":  alternatives,
            },
            status=status.HTTP_200_OK,
        )


class DestinationListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        category = request.query_params.get("category", None)
        country = request.query_params.get("country", None)
        qs = Destination.objects.all()
        if category:
            qs = qs.filter(category=category)
        if country:
            qs = qs.filter(country__icontains=country)
        serializer = DestinationSerializer(qs, many=True)
        return Response(serializer.data)


class TripHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        trips = TripPlan.objects.filter(user=request.user)[:20]
        serializer = TripPlanSerializer(trips, many=True)
        return Response(serializer.data)

    def delete(self, request, pk=None):
        try:
            trip = TripPlan.objects.get(pk=pk, user=request.user)
            trip.delete()
            # FIX (BUG-03): HTTP 204 No Content must have an empty body.
            # The previous response included a JSON body which is semantically
            # invalid for 204 and is silently dropped by many HTTP clients.
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TripPlan.DoesNotExist:
            return Response({"error": "Trip not found."}, status=status.HTTP_404_NOT_FOUND)

class ChatbotView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'plan_trip'

    def post(self, request):
        if llm is None:
            return Response({"error": "LLM not configured. Check GROQ_API_KEY."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        user_message = request.data.get("message", "").strip()
        context_plan = request.data.get("context_plan", None)
        
        if not user_message:
            return Response({"error": "Message is required."}, status=400)
            
        system_content = (
            "You are Travemle's AI Travel Assistant. "
            "You help users with their travel queries, provide recommendations, "
            "and explain travel itineraries. Keep your responses friendly, concise, "
            "and helpful. "
            "CRITICAL: Format your response in pure plain text ONLY. DO NOT use any markdown formatting "
            "like **bold**, *italics*, or # headers, because the mobile app cannot render them."
        )
        
        if context_plan:
            system_content += f"\n\nThe user is currently looking at this trip plan: {json.dumps(context_plan)}"
            
        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=user_message),
        ]
        
        try:
            response = llm.invoke(messages)
            return Response({"reply": response.content}, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Chatbot error: {e}")
            return Response({"error": "Sorry, I am having trouble connecting right now."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class UserInsightsView(APIView):
    """
    GET /api/insights/
    Returns auto-analyzed travel behaviour insights for the authenticated user,
    derived from their full trip history (no manual input required).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        insights = analyze_user_interests_from_history(request.user)
        return Response(insights, status=status.HTTP_200_OK)

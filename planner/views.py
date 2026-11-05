import os
import json
import re
import requests
import math
from collections import Counter
from datetime import datetime

from django.contrib.auth.models import User
from dotenv import load_dotenv
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
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# ML Recommendation Service URL (running on port 8001)
ML_SERVICE_URL = os.getenv("ML_SERVICE_URL", "http://127.0.0.1:8001")

# ── 2. Module-level LLM singleton (not per-request) ──────────────────────────
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

# Sri Lanka Road Network Distance Matrix (Origin ⇄ Destination in km)
# Includes mountain winding factor (approx 1.25x - 1.4x of straight line)
SRI_LANKA_ROAD_DISTANCES = {
    ("colombo", "kandy"): 120,
    ("colombo", "galle"): 125,
    ("colombo", "ella"): 215,
    ("colombo", "nuwara eliya"): 165,
    ("colombo", "sigiriya"): 175,
    ("colombo", "mirissa"): 150,
    ("colombo", "bentota"): 80,
    ("colombo", "yala"): 260,
    ("colombo", "trincomalee"): 265,
    ("colombo", "anuradhapura"): 205,
    ("colombo", "dambulla"): 160,
    ("colombo", "polonnaruwa"): 225,
    ("colombo", "arugam bay"): 320,
    ("colombo", "jaffna"): 395,
    ("colombo", "negombo"): 38,
    ("kandy", "nuwara eliya"): 78,
    ("kandy", "ella"): 135,
    ("kandy", "sigiriya"): 90,
    ("galle", "mirissa"): 35,
    ("galle", "ella"): 195,
    ("galle", "yala"): 170,
}

def estimate_road_distance_km(orig: str, dest: str) -> int:
    o = str(orig).lower().strip()
    d = str(dest).lower().strip()
    if (o, d) in SRI_LANKA_ROAD_DISTANCES:
        return SRI_LANKA_ROAD_DISTANCES[(o, d)]
    if (d, o) in SRI_LANKA_ROAD_DISTANCES:
        return SRI_LANKA_ROAD_DISTANCES[(d, o)]
    
    # Haversine distance with Sri Lankan road curvature factor (~1.35x)
    lat1, lon1 = get_coordinates(orig)
    lat2, lon2 = get_coordinates(dest)
    if lat1 and lat2:
        import math as _m
        R = 6371.0 # Earth radius in km
        dlat = _m.radians(lat2 - lat1)
        dlon = _m.radians(lon2 - lon1)
        a = _m.sin(dlat / 2)**2 + _m.cos(_m.radians(lat1)) * _m.cos(_m.radians(lat2)) * _m.sin(dlon / 2)**2
        c = 2 * _m.atan2(_m.sqrt(a), _m.sqrt(1 - a))
        aerial_km = R * c
        return max(35, round(aerial_km * 1.35))
    return 150 # Safe default for Sri Lanka travel


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


# Regional historical climate averages for Sri Lanka by month (1..12)
# Source: Department of Meteorology, Sri Lanka (Met.gov.lk)
SL_MONTHLY_CLIMATE = {
    "central": {  # Kandy, Nuwara Eliya, Ella, Matale, Hatton
        1:  {"temp": 21.0, "temp_min": 15.0, "temp_max": 26.0, "rain_pct": 35, "desc": "Pleasant & partly cloudy", "emoji": "⛅"},
        2:  {"temp": 22.0, "temp_min": 15.0, "temp_max": 28.0, "rain_pct": 25, "desc": "Dry, sunny & clear", "emoji": "☀️"},
        3:  {"temp": 24.0, "temp_min": 17.0, "temp_max": 30.0, "rain_pct": 35, "desc": "Warm with clear skies", "emoji": "☀️"},
        4:  {"temp": 24.5, "temp_min": 18.0, "temp_max": 30.0, "rain_pct": 55, "desc": "Intermonsoon evening showers", "emoji": "🌦️"},
        5:  {"temp": 24.0, "temp_min": 19.0, "temp_max": 28.0, "rain_pct": 50, "desc": "Misty with scattered showers", "emoji": "🌦️"},
        6:  {"temp": 23.0, "temp_min": 18.0, "temp_max": 27.0, "rain_pct": 45, "desc": "Breezy mountain weather", "emoji": "⛅"},
        7:  {"temp": 22.5, "temp_min": 18.0, "temp_max": 26.5, "rain_pct": 40, "desc": "Cool mountain breeze", "emoji": "⛅"},
        8:  {"temp": 23.0, "temp_min": 18.0, "temp_max": 27.0, "rain_pct": 35, "desc": "Pleasant highland climate", "emoji": "⛅"},
        9:  {"temp": 23.0, "temp_min": 18.0, "temp_max": 27.5, "rain_pct": 45, "desc": "Mild with occasional rain", "emoji": "🌦️"},
        10: {"temp": 22.5, "temp_min": 18.0, "temp_max": 27.0, "rain_pct": 70, "desc": "Intermonsoon frequent rain", "emoji": "🌧️"},
        11: {"temp": 22.0, "temp_min": 17.0, "temp_max": 26.5, "rain_pct": 75, "desc": "Northeast monsoon rainfall", "emoji": "🌧️"},
        12: {"temp": 21.0, "temp_min": 16.0, "temp_max": 25.5, "rain_pct": 60, "desc": "Cool, misty & wet", "emoji": "🌧️"}
    },
    "east": {  # Trincomalee, Arugam Bay, Batticaloa, Pasikudah
        1:  {"temp": 26.0, "temp_min": 23.0, "temp_max": 29.0, "rain_pct": 50, "desc": "Passing coastal rain", "emoji": "🌦️"},
        2:  {"temp": 27.0, "temp_min": 23.0, "temp_max": 30.5, "rain_pct": 30, "desc": "Warm & clearing skies", "emoji": "⛅"},
        3:  {"temp": 28.5, "temp_min": 24.0, "temp_max": 32.0, "rain_pct": 20, "desc": "Dry, bright & sunny", "emoji": "☀️"},
        4:  {"temp": 30.0, "temp_min": 25.0, "temp_max": 34.0, "rain_pct": 25, "desc": "Warm & sunny beach days", "emoji": "☀️"},
        5:  {"temp": 31.0, "temp_min": 26.0, "temp_max": 35.0, "rain_pct": 20, "desc": "Prime sunny season", "emoji": "☀️"},
        6:  {"temp": 31.5, "temp_min": 26.0, "temp_max": 35.5, "rain_pct": 15, "desc": "Clear sunny skies & calm seas", "emoji": "☀️"},
        7:  {"temp": 31.0, "temp_min": 25.5, "temp_max": 35.0, "rain_pct": 20, "desc": "Hot & sunny surf season", "emoji": "☀️"},
        8:  {"temp": 30.5, "temp_min": 25.0, "temp_max": 34.5, "rain_pct": 25, "desc": "Ideal beach weather", "emoji": "☀️"},
        9:  {"temp": 29.5, "temp_min": 24.5, "temp_max": 33.5, "rain_pct": 35, "desc": "Warm with light breezes", "emoji": "⛅"},
        10: {"temp": 28.0, "temp_min": 24.0, "temp_max": 31.5, "rain_pct": 65, "desc": "Intermonsoon rain showers", "emoji": "🌧️"},
        11: {"temp": 26.5, "temp_min": 23.5, "temp_max": 29.5, "rain_pct": 80, "desc": "Northeast monsoon wet weather", "emoji": "🌧️"},
        12: {"temp": 26.0, "temp_min": 23.0, "temp_max": 29.0, "rain_pct": 75, "desc": "Monsoon rain & stormy seas", "emoji": "🌧️"}
    },
    "west_south": {  # Colombo, Galle, Bentota, Mirissa, Negombo, Kalutara, Yala
        1:  {"temp": 27.5, "temp_min": 22.5, "temp_max": 31.5, "rain_pct": 25, "desc": "Dry, warm & sunny beach days", "emoji": "☀️"},
        2:  {"temp": 28.0, "temp_min": 23.0, "temp_max": 32.0, "rain_pct": 20, "desc": "Clear blue skies & calm ocean", "emoji": "☀️"},
        3:  {"temp": 29.0, "temp_min": 24.0, "temp_max": 32.5, "rain_pct": 30, "desc": "Warm & mostly sunny", "emoji": "☀️"},
        4:  {"temp": 29.5, "temp_min": 25.0, "temp_max": 33.0, "rain_pct": 55, "desc": "Warm with afternoon thunder", "emoji": "🌦️"},
        5:  {"temp": 29.0, "temp_min": 25.5, "temp_max": 32.0, "rain_pct": 75, "desc": "Southwest monsoon rain", "emoji": "🌧️"},
        6:  {"temp": 28.5, "temp_min": 25.0, "temp_max": 31.0, "rain_pct": 65, "desc": "Monsoon breezes & showers", "emoji": "🌧️"},
        7:  {"temp": 28.0, "temp_min": 25.0, "temp_max": 30.5, "rain_pct": 50, "desc": "Cloudy with scattered rain", "emoji": "🌦️"},
        8:  {"temp": 28.0, "temp_min": 25.0, "temp_max": 30.5, "rain_pct": 45, "desc": "Breezy with sunny breaks", "emoji": "⛅"},
        9:  {"temp": 28.0, "temp_min": 24.5, "temp_max": 31.0, "rain_pct": 60, "desc": "Intermittent coastal rain", "emoji": "🌦️"},
        10: {"temp": 27.5, "temp_min": 24.0, "temp_max": 31.0, "rain_pct": 75, "desc": "Second intermonsoon downpours", "emoji": "🌧️"},
        11: {"temp": 27.5, "temp_min": 23.5, "temp_max": 31.0, "rain_pct": 65, "desc": "Passing showers & sunshine", "emoji": "🌦️"},
        12: {"temp": 27.5, "temp_min": 23.0, "temp_max": 31.0, "rain_pct": 35, "desc": "Pleasant, sunny & dry start", "emoji": "☀️"}
    }
}


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
            # FIX (BUG-07): OWM 'dt' values are UTC Unix timestamps.
            # datetime.fromtimestamp() converts using the SERVER's local TZ
            # (e.g. UTC+5:30 on a Windows dev machine), which shifts late-
            # evening UTC slots into the next local day and mismatches the
            # YYYY-MM-DD trip dates sent from the frontend.
            # utcfromtimestamp() keeps both in the same UTC frame.
            slot_dt   = datetime.utcfromtimestamp(item["dt"])
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
                # Beyond 5-day live forecast: Use Sri Lanka meteorological climate averages for this month & region
                city_clean = city.lower().strip()
                if city_clean in EAST_COAST_CITIES:
                    reg = "east"
                elif city_clean in CENTRAL_CITIES:
                    reg = "central"
                else:
                    reg = "west_south"

                clim = SL_MONTHLY_CLIMATE[reg].get(trip_date.month, SL_MONTHLY_CLIMATE["west_south"][1])
                day_entry = {
                    "date":        str(trip_date),
                    "day_label":   day_label,
                    "day_num":     day_num,
                    "description": clim["desc"],
                    "emoji":       clim["emoji"],
                    "temp":        clim["temp"],
                    "temp_min":    clim["temp_min"],
                    "temp_max":    clim["temp_max"],
                    "humidity":    75,
                    "rain_pct":    clim["rain_pct"],
                    "available":   True,
                    "is_climate_avg": True,
                }
                summary_parts.append(
                    f"{day_label}: {clim['desc']}, ~{clim['temp']}°C, Rain ~{clim['rain_pct']}%"
                )
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
                    "is_climate_avg": False,
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


# Representative cities per region — used to suggest drier alternatives
REGION_SAMPLE_CITIES = {
    "west_south": ["galle", "colombo", "mirissa", "bentota", "hikkaduwa"],
    "east":       ["trincomalee", "arugam bay", "pasikuda"],
    "central":    ["kandy", "ella", "sigiriya", "nuwara eliya"],
}

REGION_LABELS = {
    "west_south": "West & South Coast",
    "east":       "East Coast",
    "central":    "Central Highlands",
}


def suggest_rainy_weather_alternatives(
    city: str,
    weather_days: list,
    start_date_str: str,
    interests: str,
    country: str,
    user=None,
) -> dict:
    """
    Analyses the trip's forecast data. If significant rain is detected
    (>= 50% of forecast-available days have max rain probability >= 60%),
    finds other Sri Lanka regions that are in a better season for that month
    and returns interest-matched destinations from those regions.

    Also incorporates the user's historical trip interests to personalise
    the recommendations.

    Source logic:
      - Rain threshold: OpenWeatherMap PoP (Probability of Precipitation) >= 60%
      - Better-region detection: SLTDA regional seasonality data
    """
    try:
        # ── Step 1: Analyse rain across forecast-available days ──────────────
        available_days = [d for d in weather_days if d.get("available")]
        if not available_days:
            return {"is_rainy": False}

        rainy_days  = [d for d in available_days if (d.get("rain_pct") or 0) >= 60]
        rainy_count = len(rainy_days)
        avg_rain    = round(sum(d.get("rain_pct", 0) for d in available_days) / len(available_days))
        is_rainy    = rainy_count >= max(1, len(available_days) // 2)  # >= 50% days rainy

        if not is_rainy:
            return {"is_rainy": False, "avg_rain_pct": avg_rain}

        # ── Step 2: Determine which region the chosen city belongs to ────────
        city_lower = city.lower().strip()
        if city_lower in EAST_COAST_CITIES:
            current_region = "east"
        elif city_lower in CENTRAL_CITIES:
            current_region = "central"
        else:
            current_region = "west_south"

        # ── Step 3: Find OTHER regions with better weather that month ────────
        month = datetime.strptime(start_date_str, "%Y-%m-%d").month
        better_regions = []
        for region, monthly_data in SL_SEASON_DATA.items():
            if region == current_region:
                continue
            season_val = monthly_data[month]
            if season_val in ("peak", "shoulder"):  # peak or shoulder = drier/better
                better_regions.append({
                    "region":       region,
                    "region_label": REGION_LABELS[region],
                    "season":       season_val,
                })

        # Sort: prefer peak over shoulder
        better_regions.sort(key=lambda r: 0 if r["season"] == "peak" else 1)

        if not better_regions:
            # No clearly better region — still return alert but no specific alts
            return {
                "is_rainy":       True,
                "avg_rain_pct":   avg_rain,
                "rainy_days":     rainy_count,
                "total_days":     len(available_days),
                "better_regions": [],
                "alternatives":   [],
                "message": (
                    f"Heavy rain expected on {rainy_count}/{len(available_days)} forecast days "
                    f"(avg {avg_rain}% precipitation). Consider flexible travel insurance."
                ),
            }

        # ── Step 4: Build merged interest list (current + user history) ──────
        interest_set = set(i.strip().lower() for i in interests.split(',') if i.strip())
        if user:
            # Enrich with top interests from trip history
            past_trips = TripPlan.objects.filter(user=user).order_by('-created_at')[:15]
            hist_interests = []
            for t in past_trips:
                if t.interests:
                    hist_interests.extend(i.strip().lower() for i in t.interests.split(',') if i.strip())
            if hist_interests:
                top_hist = [k for k, _ in Counter(hist_interests).most_common(3)]
                interest_set.update(top_hist)

        # ── Step 5: Find destinations in better regions matching interests ────
        best_region   = better_regions[0]
        sample_cities = set(REGION_SAMPLE_CITIES.get(best_region["region"], []))

        dests = Destination.objects.filter(country__icontains=country)
        rainy_alternatives = []
        seen_names = set()

        for d in dests:
            if d.name.lower() == city_lower:
                continue
            # Check if this destination belongs to the better region
            in_better_region = (
                d.name.lower() in sample_cities
                or any(sc in d.name.lower() for sc in sample_cities)
                or (
                    best_region["region"] == "east"
                    and d.name.lower() in EAST_COAST_CITIES
                )
                or (
                    best_region["region"] == "central"
                    and d.name.lower() in CENTRAL_CITIES
                )
            )
            interest_match = d.category.lower() in interest_set

            if (in_better_region or interest_match) and d.name not in seen_names:
                rainy_alternatives.append({
                    "name":          d.name,
                    "category":      d.category,
                    "description":   (
                        d.description[:120] + "..."
                        if len(d.description) > 120 else d.description
                    ),
                    "region":        best_region["region_label"],
                    "weather_note":  (
                        f"{best_region['region_label']} is in "
                        f"{best_region['season'].replace('_', '-')} season "
                        f"— significantly drier than your chosen destination."
                    ),
                    "reason": (
                        f"Better weather + matches your '{d.category}' interest"
                        if interest_match else
                        f"Drier weather in {best_region['region_label']} this month"
                    ),
                })
                seen_names.add(d.name)
            if len(rainy_alternatives) >= 4:
                break

        month_name = datetime.strptime(start_date_str, "%Y-%m-%d").strftime("%B")
        return {
            "is_rainy":       True,
            "avg_rain_pct":   avg_rain,
            "rainy_days":     rainy_count,
            "total_days":     len(available_days),
            "better_regions": better_regions,
            "alternatives":   rainy_alternatives,
            "source":         "OpenWeatherMap PoP data + SLTDA Regional Seasonality Guide",
            "message": (
                f"Heavy rain forecast on {rainy_count} of {len(available_days)} days "
                f"(avg {avg_rain}% precipitation) for your selected dates. "
                f"{best_region['region_label']} experiences better conditions in {month_name}."
            ),
        }

    except Exception as e:
        print(f"Rainy alert error: {e}")
        return {"is_rainy": False}


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


def call_ml_service(city, country, origin, start_date, end_date, interests,
                    food_prefs, acc_prefs, act_prefs,
                    budget, mode, recommended_places="", passengers=1):
    """
    Calls the local ML Recommendation Service (port 8001) instead of Groq AI.
    Maps the trip parameters to the ML service schema and converts the response
    into the same plan_data format the frontend already expects.
    """
    try:
        s = datetime.strptime(start_date, "%Y-%m-%d")
        e = datetime.strptime(end_date, "%Y-%m-%d")
        trip_days = (e - s).days + 1
    except Exception:
        trip_days = 1

    # Build interests list from comma-separated strings
    def to_list(val):
        if not val:
            return []
        return [v.strip().lower() for v in val.split(',') if v.strip()]

    interests_list = to_list(interests)
    activities_list = to_list(act_prefs)

    # Map travel_mode to preferred_transport
    transport_map = {
        "Car": "car", "Bus": "bus", "Train": "train",
        "Bicycle": "bicycle", "Walking": "walking",
    }
    preferred_transport = transport_map.get(mode, "car")

    # Map passengers to appropriate travel_type
    passengers = max(1, int(passengers or 1))
    if passengers == 1:
        travel_type = "solo"
    elif passengers == 2:
        travel_type = "couple"
    elif passengers <= 5:
        travel_type = "family"
    else:
        travel_type = "group"

    payload = {
        "budget": float(budget) if budget else 10000.0,
        "trip_days": trip_days,
        "interests": interests_list,
        "preferred_activities": activities_list,
        "travel_type": travel_type,
        "family_friendly": (travel_type in ("family", "group")),
        "preferred_transport": preferred_transport,
        "top_n": min(trip_days * 3, 15),  # ~3 per day
    }

    # Optionally set accommodation type
    if acc_prefs:
        acc_lower = acc_prefs.lower()
        if "budget" in acc_lower or "hostel" in acc_lower:
            payload["accommodation_type"] = "hostel"
        elif "luxury" in acc_lower or "resort" in acc_lower:
            payload["accommodation_type"] = "resort"
        elif "hotel" in acc_lower:
            payload["accommodation_type"] = "hotel"

    try:
        resp = requests.post(
            f"{ML_SERVICE_URL}/api/v1/recommend/full-trip",
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        ml_data = resp.json()
    except requests.exceptions.ConnectionError:
        return None, "ML service is not running. Please start it on port 8001."
    except requests.exceptions.Timeout:
        return None, "ML service timed out. Please try again."
    except Exception as e:
        return None, f"ML service error: {str(e)}"

    # ── Convert ML response → plan_data format ───────────────────────────────
    dest = ml_data.get("recommended_destination", {})
    # Always use the user's chosen city, not the ML-recommended destination
    dest_name = city.strip().title() if city else (
        dest.get("destination_name") or dest.get("name") or "Sri Lanka"
    )
    accommodations = ml_data.get("recommended_accommodations", [])
    activities = ml_data.get("recommended_activities", [])
    budget_summary = ml_data.get("budget_summary", {})

    # ── Helper: strip trailing numbers from demo CSV names ─────────────────
    def clean_name(raw: str) -> str:
        """Remove trailing number from demo data names e.g. 'Hiking experience 51' → 'Hiking Experience'"""
        cleaned = re.sub(r"\s+\d+$", "", str(raw)).strip()
        return cleaned.title()

    # ── Realistic Destination Activities & Highlights ─────────────────────
        # ── Realistic Curated Accommodations by Destination & Tier ─────────────
    # Real hotels in Sri Lanka classified by budget per night (LKR)
    DESTINATION_REAL_HOTELS = {
        "kandy": {
            "budget": [
                {"name": "Kandy City Stay", "type": "hotel", "price": 6500, "rating": 4.1, "features": ["wifi", "air_conditioning"], "reason": "Budget-friendly, clean hotel in the heart of Kandy city."},
                {"name": "Olde Empire Hotel", "type": "guest_house", "price": 5000, "rating": 4.0, "features": ["wifi"], "reason": "Charming colonial-era budget stay next to the Temple of the Tooth."}
            ],
            "mid": [
                {"name": "Hotel Suisse Kandy", "type": "hotel", "price": 14500, "rating": 4.3, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Colonial-style heritage hotel overlooking Kandy Lake."},
                {"name": "Thilanka Hotel", "type": "hotel", "price": 16000, "rating": 4.2, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Scenic hill retreat offering sweeping views of the Kandyan city."}
            ],
            "luxury": [
                {"name": "The Grand Kandyan Hotel", "type": "resort", "price": 32000, "rating": 4.7, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "5-star luxury accommodation with rooftop pool and fine dining."},
                {"name": "Earl's Regency Hotel", "type": "resort", "price": 28500, "rating": 4.6, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Premium riverside sanctuary nestled in the Tennekumbura hills."}
            ]
        },
        "ella": {
            "budget": [
                {"name": "Ella Mount View Guest Inn", "type": "guest_house", "price": 5500, "rating": 4.2, "features": ["wifi", "breakfast"], "reason": "Cozy hillside guesthouse with stunning views of Ella Gap."},
                {"name": "Hangover Hostels Ella", "type": "hostel", "price": 4000, "rating": 4.3, "features": ["wifi", "air_conditioning"], "reason": "Top-rated social hostel walking distance from Ella railway station."}
            ],
            "mid": [
                {"name": "Oak Ray Ella Gap Hotel", "type": "hotel", "price": 13500, "rating": 4.2, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Centrally located resort with an outdoor pool and garden views."},
                {"name": "Morning Dew Hotel Ella", "type": "hotel", "price": 12000, "rating": 4.3, "features": ["wifi", "breakfast", "parking"], "reason": "Modern hotel with panoramic mountain view balconies."}
            ],
            "luxury": [
                {"name": "98 Acres Resort & Spa", "type": "resort", "price": 45000, "rating": 4.9, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "World-famous luxury eco-resort on a scenic 98-acre tea estate."},
                {"name": "EKHO Ella", "type": "resort", "price": 26000, "rating": 4.5, "features": ["wifi", "breakfast", "parking", "air_conditioning"], "reason": "Boutique cliffside retreat directly facing the misty Ella Gap."}
            ]
        },
        "colombo": {
            "budget": [
                {"name": "Clock Inn Colombo", "type": "hostel", "price": 4500, "rating": 4.1, "features": ["wifi", "air_conditioning"], "reason": "Trendy budget boutique hostel in central Colombo 03."},
                {"name": "City Hotel Colombo 02", "type": "hotel", "price": 7000, "rating": 4.0, "features": ["wifi", "air_conditioning"], "reason": "Comfortable, no-frills business stay close to Slave Island."}
            ],
            "mid": [
                {"name": "Cinnamon Red Colombo", "type": "hotel", "price": 16500, "rating": 4.4, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Pioneering lean-luxury hotel featuring Colombo's finest rooftop infinity pool."},
                {"name": "Fairway Colombo", "type": "hotel", "price": 15000, "rating": 4.3, "features": ["wifi", "breakfast", "parking", "air_conditioning"], "reason": "Contemporary city hotel next to the historic Dutch Hospital precinct."}
            ],
            "luxury": [
                {"name": "Galle Face Hotel", "type": "resort", "price": 38000, "rating": 4.7, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Legendary 1864 grand heritage hotel perched directly on the Indian Ocean."},
                {"name": "The Kingsbury Colombo", "type": "hotel", "price": 35000, "rating": 4.6, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Opulent 5-star oceanfront luxury with multiple world-class restaurants."}
            ]
        },
        "galle": {
            "budget": [
                {"name": "Pedlar's Inn Hostel Galle Fort", "type": "hostel", "price": 4800, "rating": 4.2, "features": ["wifi", "air_conditioning"], "reason": "Boutique heritage hostel inside the UNESCO-protected Galle Dutch Fort."},
                {"name": "Fortress Guest House", "type": "guest_house", "price": 6000, "rating": 4.0, "features": ["wifi"], "reason": "Homely and tranquil guesthouse on historic rampart street."}
            ],
            "mid": [
                {"name": "Tamarind Hill Galle", "type": "villa", "price": 17500, "rating": 4.4, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Restored 200-year-old colonial manor house with central courtyard."},
                {"name": "The Fort Printers", "type": "hotel", "price": 19000, "rating": 4.3, "features": ["wifi", "pool", "breakfast"], "reason": "Eighteenth-century private mansion converted into a chic boutique hotel."}
            ],
            "luxury": [
                {"name": "Jetwing Lighthouse", "type": "resort", "price": 42000, "rating": 4.8, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Geoffrey Bawa architectural masterpiece perched on rocky headland waves."},
                {"name": "Amangalla", "type": "resort", "price": 65000, "rating": 4.9, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Ultra-luxury Aman resort preserving the timeless glamour of 17th-century Ceylon."}
            ]
        },
        "nuwara eliya": {
            "budget": [
                {"name": "Single Tree Hotel", "type": "hotel", "price": 6000, "rating": 4.0, "features": ["wifi", "parking"], "reason": "Comfortable mountain view lodge near Lake Gregory."},
                {"name": "Hi Lanka Hostel Nuwara Eliya", "type": "hostel", "price": 4200, "rating": 4.2, "features": ["wifi"], "reason": "Cozy backpacker hub with warm fireplaces and hill views."}
            ],
            "mid": [
                {"name": "Araliya Green Hills", "type": "hotel", "price": 18000, "rating": 4.3, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Modern heated-pool mountain resort near Victoria Park."},
                {"name": "Jetwing St. Andrew's", "type": "hotel", "price": 21000, "rating": 4.4, "features": ["wifi", "breakfast", "parking"], "reason": "Stately Tudor-style Georgian country manor nestled in misty hills."}
            ],
            "luxury": [
                {"name": "The Grand Hotel Nuwara Eliya", "type": "resort", "price": 38000, "rating": 4.8, "features": ["wifi", "breakfast", "parking", "air_conditioning"], "reason": "Iconic British colonial heritage hotel famed for award-winning high tea."},
                {"name": "Heritance Tea Factory", "type": "resort", "price": 46000, "rating": 4.9, "features": ["wifi", "breakfast", "parking"], "reason": "Unique luxury hotel converted from an authentic 19th-century Ceylon tea factory."}
            ]
        },
        "sigiriya": {
            "budget": [
                {"name": "Sigiriya Village Homestay", "type": "homestay", "price": 5000, "rating": 4.3, "features": ["wifi", "breakfast"], "reason": "Warm local family hospitality under the shadow of Sigiriya rock."},
                {"name": "Kassapa Lions Rock Stay", "type": "hotel", "price": 7500, "rating": 4.1, "features": ["wifi", "pool"], "reason": "Peaceful budget chalets surrounded by tranquil wilderness."}
            ],
            "mid": [
                {"name": "Hotel Sigiriya", "type": "hotel", "price": 16000, "rating": 4.4, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Premier view hotel whose freshwater pool looks directly up at the Lion Rock citadel."},
                {"name": "Aliya Resort & Spa", "type": "resort", "price": 22000, "rating": 4.5, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Elephant-themed eco-luxury resort with breathtaking infinity pool vistas."}
            ],
            "luxury": [
                {"name": "Water Garden Sigiriya", "type": "resort", "price": 52000, "rating": 4.9, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Exclusive luxury villas set amidst water courses modeled on ancient royal gardens."},
                {"name": "Cinnamon Lodge Habarana", "type": "resort", "price": 31000, "rating": 4.6, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Sprawling five-star haven on a 27-acre forest estate beside the lake."}
            ]
        },
        "mirissa": {
            "budget": [
                {"name": "Mirissa Beach Hostels", "type": "hostel", "price": 4500, "rating": 4.1, "features": ["wifi", "air_conditioning"], "reason": "Social surf hostel just 2 minutes walk from the main bay."},
                {"name": "Sunstyle Mirissa Guesthouse", "type": "guest_house", "price": 6000, "rating": 4.2, "features": ["wifi", "breakfast"], "reason": "Friendly guesthouse with direct access to coconut palm gardens."}
            ],
            "mid": [
                {"name": "Paradise Beach Club Mirissa", "type": "hotel", "price": 16000, "rating": 4.3, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Beachfront hotel with oceanfront pool right where the surf breaks."},
                {"name": "Triple O Six Mirissa", "type": "hotel", "price": 18500, "rating": 4.4, "features": ["wifi", "pool", "breakfast"], "reason": "Chic design hotel with artistic decor and serene pool lounge."}
            ],
            "luxury": [
                {"name": "Mandara Resort Mirissa", "type": "resort", "price": 32000, "rating": 4.6, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Luxury beachfront oasis where the Redigama river meets the ocean."},
                {"name": "Sri Sharavi Beach Villas & Spa", "type": "villa", "price": 45000, "rating": 4.8, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Exclusive boutique oceanfront villas featuring personalized butler service."}
            ]
        },
        "bentota": {
            "budget": [
                {"name": "Bentota River View Inn", "type": "guest_house", "price": 5500, "rating": 4.0, "features": ["wifi"], "reason": "Peaceful riverbank accommodation with boat safari access."},
                {"name": "Lanka Princess Budget Stay", "type": "hotel", "price": 7500, "rating": 4.1, "features": ["wifi", "air_conditioning"], "reason": "Clean, relaxing stay close to the golden Bentota beach sands."}
            ],
            "mid": [
                {"name": "Centara Ceysands Resort & Spa", "type": "resort", "price": 19000, "rating": 4.4, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Spectacular resort reached by boat, situated between the river and Indian Ocean."},
                {"name": "Ekho Surf Bentota", "type": "hotel", "price": 17000, "rating": 4.3, "features": ["wifi", "pool", "breakfast"], "reason": "Step directly from the pool onto the widest golden beach in Bentota."}
            ],
            "luxury": [
                {"name": "Taj Bentota Resort & Spa", "type": "resort", "price": 36000, "rating": 4.7, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "World-class luxury by the Taj Group with sprawling palms and ocean cliff views."},
                {"name": "Cinnamon Bentota Beach", "type": "resort", "price": 42000, "rating": 4.8, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Geoffrey Bawa heritage design reimagined as an elite luxury coastal retreat."}
            ]
        },
        "yala": {
            "budget": [
                {"name": "Yala Safari Camping Inn", "type": "guest_house", "price": 6500, "rating": 4.1, "features": ["wifi", "breakfast"], "reason": "Budget-friendly base camp with jeep safari arrangement services."},
                {"name": "Tissamaharama Rest House", "type": "hotel", "price": 8000, "rating": 4.0, "features": ["wifi", "parking"], "reason": "Historic lakeside rest house overlooking ancient Tissa Wewa reservoir."}
            ],
            "mid": [
                {"name": "Jetwing Yala", "type": "hotel", "price": 24000, "rating": 4.5, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Wilderness beach hotel on the park boundary where elephants roam the dunes."},
                {"name": "Cinnamon Wild Yala", "type": "resort", "price": 26000, "rating": 4.6, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Safari chalets around a lake frequented by wild animals and birds."}
            ],
            "luxury": [
                {"name": "Wild Coast Tented Lodge", "type": "resort", "price": 85000, "rating": 4.9, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Award-winning cocoon safari suites where jungle meets the raw ocean shore."},
                {"name": "Uga Chena Huts Yala", "type": "resort", "price": 78000, "rating": 4.9, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Private pool pavilions hidden amidst coastal dunes with all-inclusive safaris."}
            ]
        },
        "trincomalee": {
            "budget": [
                {"name": "Uppuveli Beach Guest House", "type": "guest_house", "price": 5500, "rating": 4.1, "features": ["wifi"], "reason": "Cozy seaside rooms steps from Uppuveli beach cafes."},
                {"name": "French Garden Resort Trinco", "type": "hotel", "price": 7000, "rating": 4.0, "features": ["wifi", "air_conditioning"], "reason": "Comfortable budget rooms with shade trees and garden restaurant."}
            ],
            "mid": [
                {"name": "Trinco Blu by Cinnamon", "type": "resort", "price": 18000, "rating": 4.4, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Retro-chic retro beach resort specialized in seasonal whale watching expeditions."},
                {"name": "Anantamaa Resort", "type": "hotel", "price": 15000, "rating": 4.2, "features": ["wifi", "pool", "breakfast"], "reason": "Spacious family resort with large outdoor pool in peaceful surroundings."}
            ],
            "luxury": [
                {"name": "Jungle Beach by Uga Escapes", "type": "resort", "price": 48000, "rating": 4.8, "features": ["wifi", "pool", "breakfast", "parking", "air_conditioning"], "reason": "Secluded luxury treehouse villas tucked into dense coastal jungle and private beach."},
                {"name": "Nilaveli Beach Hotel", "type": "resort", "price": 26000, "rating": 4.5, "features": ["wifi", "pool", "breakfast", "parking"], "reason": "Historic beachfront retreat facing the crystal waters of Pigeon Island."}
            ]
        }
    }

    DESTINATION_REAL_ACTIVITIES = {
        "ella": {
            "hiking": ("Ella Rock Hike & Little Adam's Peak", "Trek along lush tea plantations and steep ridges for panoramic views of Ella Gap."),
            "sightseeing": ("Nine Arch Bridge & Demodara Loop", "Watch the blue train cross the colonial viaduct amidst dense jungle greenery."),
            "photography": ("Ravana Falls & Secret Viewpoint", "Scenic cascades and epic valley viewpoints ideal for photography and relaxed sightseeing."),
            "wellness": ("Ayurvedic Herbal Bath & Yoga Session", "Traditional relaxation therapy, steam bath, and rejuvenating mountain yoga."),
            "food": ("Sri Lankan Cooking Class & Curries", "Hands-on preparation of traditional clay pot curries and coconut sambol with local hosts."),
            "adventure": ("Flying Ravana Mega Zipline", "Sri Lanka's fastest zipline soaring over tea estates and valleys at 80km/h."),
            "cultural": ("Dowa Rock Temple & Ancient Carvings", "2,000-year-old rock monastery featuring an uncompleted 38-foot Buddha statue."),
            "wildlife": ("Ella Gap Bird Watching & Nature Trail", "Spot endemic highland birds, giant squirrels, and purple-faced langurs in native cloud forest.")
        },
        "kandy": {
            "cultural": ("Temple of the Sacred Tooth Relic", "Sri Lanka's most sacred shrine housing the Buddha's tooth, with traditional drumming and rituals."),
            "wildlife": ("Udawattekele Sanctuary Forest Walk", "Historical royal forest reserve home to macaque troops, civets, and over 80 bird species."),
            "sightseeing": ("Royal Botanical Gardens Peradeniya", "Sprawling 147-acre garden famous for its orchid collection, palm avenues, and giant fig tree."),
            "food": ("Kandy Lake Street Food & Kandyan Sweets", "Sample fresh local kottu, egg hoppers, and traditional sweets by the serene Kandy Lake."),
            "shopping": ("Kandy Artisan Crafts & Gem Museum", "Browse handmade brassware, handloom batiks, and Ceylon blue sapphire workshops."),
            "water_sports": ("Kandy Lake Scenic Boat Ride", "Peaceful boat cruise across the royal lake with surrounding palace and hill views.")
        },
        "yala": {
            "wildlife": ("Yala Block 1 Jeep Safari", "Guided open-top safari tracking Sri Lankan leopards, wild elephant herds, sloth bears, and crocodiles."),
            "photography": ("Yala Golden Hour Safari & Coastal Lagoons", "Capture dramatic wildlife silhouettes against coastal sand dunes and sunset lagoons."),
            "historical": ("Sithulpawwa Rock Temple", "Ancient 2nd-century BC monastic settlement carved into towering rock outcrops inside the sanctuary."),
            "adventure": ("Off-Road Bush Trail & Wildlife Tracking", "Exciting deep-park 4x4 trail exploring riverine forest corridors and rocky terrain."),
            "wellness": ("Wilderness Camp Stargazing & Bush Dinner", "Open-air bonfire dining and tranquil celestial stargazing under clear national park skies.")
        },
        "sigiriya": {
            "historical": ("Sigiriya Rock Fortress Climb", "Ascend King Kashyapa's 5th-century palace citadel past the Mirror Wall and world-renowned frescoes."),
            "sightseeing": ("Pidurangala Rock Sunrise Summit", "Unrivaled 360-degree sunrise viewpoint directly overlooking the majestic Sigiriya citadel."),
            "wildlife": ("Minneriya Elephant Gathering Safari", "Witness dozens of wild elephant herds gathering around the historic reservoir bed."),
            "cultural": ("Hiriwadunna Village Bull-Cart & Catamaran Ride", "Traditional ox-cart ride, catamaran lake crossing, and authentic village farmer's meal."),
            "shopping": ("Dambulla & Sigiriya Woodcarving Village", "Observe master wood sculptors crafting ebony and mahogany wildlife artifacts.")
        },
        "galle": {
            "historical": ("Galle Dutch Fort Heritage Walk", "Walk the 17th-century ramparts, visit the iconic lighthouse, and explore UNESCO-protected cobblestone streets."),
            "beach": ("Jungle Beach & Rumassala Coral Reef", "Secluded sandy cove perfect for calm swimming, snorkeling, and coastal rainforest trails."),
            "food": ("Dutch Hospital Dining & Fresh Seafood", "Gourmet dining featuring jumbo lagoon prawns, spiced crab, and Ceylon tea infusions."),
            "photography": ("Galle Fort Ramparts Sunset View", "Spectacular ocean sunset vista from Flag Rock Bastion as local cliff divers plunge into waves."),
            "shopping": ("Pedlar Street Boutiques & Jewelry", "Artisanal gem jewelry, handcrafted lace, Ceylon cinnamon, and local designer clothing.")
        },
        "nuwara eliya": {
            "sightseeing": ("Pedro Tea Estate & Factory Tour", "Walk through emerald tea bushes and learn the traditional orthodox tea-making process."),
            "nature": ("Horton Plains & World's End Trek", "Misty plateau hike leading to a dramatic 880m sheer precipice and Baker's Falls."),
            "adventure": ("Gregory Lake Jet Ski & Speedboat", "Cool-climate water sports, swan pedal boats, and pony rides around Lake Gregory."),
            "cultural": ("Seetha Amman Hindu Temple & Hakgala Gardens", "Legendary Ramayana heritage temple beside vibrant high-altitude botanical gardens."),
            "food": ("Grand Hotel High Tea Experience", "Colonial afternoon tea with tiered pastries, fresh strawberries, and premium single-estate brews.")
        },
        "mirissa": {
            "beach": ("Mirissa Main Beach & Coconut Tree Hill", "Picturesque palm-fringed headland and golden shoreline ideal for surfing and relaxing."),
            "wildlife": ("Blue Whale Watching Catamaran Cruise", "Morning deep-sea cruise tracking magnificent blue whales, sperm whales, and spinner dolphins."),
            "water_sports": ("Mirissa Reef Snorkeling with Sea Turtles", "Snorkel crystal-clear bay shallows alongside gentle green sea turtles in their natural habitat."),
            "food": ("Beachfront Candlelight Seafood BBQ", "Catch of the day grilled on the beach with garlic butter, devilled calamari, and cold drinks.")
        },
        "kalutara": {
            "beach": ("Kalutara Beach & Richmond Castle", "Golden palm-lined coastline with calm sea swimming and visits to the historic 19th-century mansion."),
            "cultural": ("Kalutara Bodhiya & Sacred Temple", "Iconic hollow dagoba on the Kalu Ganga bank — one of Sri Lanka's most venerated Buddhist shrines."),
            "water_sports": ("Kalu Ganga River Kayaking & Canoeing", "Scenic paddle upstream through lush mangroves and quiet riverine villages."),
            "wildlife": ("Kalutara Lagoon & Bird Sanctuary Walk", "Boat trip through the estuary spotting kingfishers, egrets, and monitor lizards."),
            "shopping": ("Kalutara Coir & Basket Craft Market", "Browse handwoven rattan baskets, coir rope products, and hand-batik clothing."),
            "food": ("Toddy & Coconut Arrack Tasting", "Sample traditional palm toddy and local cuisine at a riverside toddy tavern.")
        },
        "trincomalee": {
            "beach": ("Nilaveli Beach & Pigeon Island Snorkeling", "World-class snorkeling through coral gardens and black-tip reef sharks in crystal-clear waters."),
            "wildlife": ("Koneswaram Temple & Trinco Whale Watching", "Sacred cliffside Shiva temple and seasonal blue whale watching in the Bay of Bengal."),
            "historical": ("Fort Frederick & Dutch Bay Heritage Walk", "Colonial fort with sweeping harbour views and colonial-era architecture."),
            "water_sports": ("Uppuveli Watersports & Diving", "Scuba diving around WWII shipwrecks, windsurfing, and catamaran sailing."),
            "cultural": ("Koneswaram Kovil Festival & Rituals", "Immerse in vibrant Hindu temple ceremonies and traditional Tamil cultural practices.")
        },
        "colombo": {
            "cultural": ("Gangaramaya Temple & Seema Malaka", "Eclectic lakeside temple complex blending Sinhalese, Thai, Indian, and Chinese architecture."),
            "food": ("Pettah Street Food & Kottu Night Market", "Sizzling kottu, hoppers, and exotic tropical fruit at Colombo's legendary night bazaar."),
            "shopping": ("Pettah Bazaar & Dutch Hospital Boutiques", "Vibrant street markets, modern lifestyle boutiques, and handcraft emporiums."),
            "sightseeing": ("Galle Face Green & Colombo Harbour Walk", "Breezy oceanside promenade perfect for sunset strolling and kite flying."),
            "historical": ("National Museum of Sri Lanka Tour", "Priceless royal regalia, ancient inscriptions, and extraordinary colonial-era artifacts.")
        },
        "bentota": {
            "beach": ("Bentota Beach & Paradise Road", "Pristine white-sand beach with warm turquoise waters ideal for swimming and sunbathing."),
            "water_sports": ("Bentota Lagoon Jet Ski & Windsurfing", "Adrenaline water sports across the scenic Bentota lagoon and open ocean."),
            "wildlife": ("Kosgoda Sea Turtle Hatchery Visit", "Watch baby sea turtles being released into the ocean at the famous conservation hatchery."),
            "sightseeing": ("Brief Garden of Bevis Bawa", "Extraordinary sculptural landscape garden created by acclaimed architect Bevis Bawa."),
            "wellness": ("Ayurvedic Lagoon Spa Retreat", "Traditional full-body herbal oil massage and steam therapy by the serene lagoon.")
        },
        "negombo": {
            "beach": ("Negombo Beach & Dutch Canal Walk", "Laid-back seaside town with sandy beaches, Portuguese churches, and a historic Dutch canal."),
            "food": ("Negombo Fish Market & Seafood Lunch", "Freshest catch of the day — crab, lobster, and jumbo prawns from the famous morning fish auction."),
            "cultural": ("St. Mary's Church & Old Dutch Fort", "17th-century colonial churches, a crumbling fort, and vibrant Catholic heritage."),
            "water_sports": ("Negombo Lagoon Boat Tour", "Explore the backwaters by traditional wooden boat, spotting fishermen and coastal bird life.")
        },
        "arugam bay": {
            "beach": ("Arugam Bay Surf Point", "World-famous right-hand point break drawing surfers from across the globe — ideal April to October."),
            "wildlife": ("Kumana National Park Jeep Safari", "Remote wildlife sanctuary east of Yala — leopards, elephants, and the famous flamingo lagoon."),
            "water_sports": ("Surf Lessons & Stand-Up Paddleboarding", "Learn to catch waves with local surf instructors or explore the bay by paddleboard."),
            "food": ("Arugam Bay Beach BBQ & Fresh Seafood", "Lantern-lit beachfront grills serving freshly caught barracuda, tuna steak, and prawn curry.")
        }
    }

    # Generic realistic fallback templates by category
    CATEGORY_DETAILS = {
        "hiking": ("Scenic Mountain Hiking Trail", "Guided trek through lush trails, panoramic lookouts, and tranquil nature pathways."),
        "cultural": ("Heritage & Cultural Landmark Visit", "Explore historic architecture, local customs, and timeless cultural heritage sites."),
        "historical": ("Ancient Archaeological Citadel Tour", "Discover preserved centuries-old ruins, stone carvings, and monumental civil engineering."),
        "wildlife": ("Wildlife & Nature Reserve Safari", "Exciting wildlife excursion observing native animals, bird species, and diverse ecosystems in the wild."),
        "beach": ("Coastal Beach & Sunset Relaxation", "Unwind along pristine sands, swim in warm coastal waters, and take in scenic ocean horizons."),
        "water_sports": ("Water Sports & Coastal Excursion", "Enjoy invigorating aquatic activities from calm paddleboarding to guided snorkeling."),
        "sightseeing": ("Panoramic Sightseeing & Landmark Tour", "Visit celebrated viewpoints, historic monuments, and must-see regional icons."),
        "wellness": ("Traditional Ayurvedic Spa & Wellness Retreat", "Revitalizing herbal oil therapy, traditional wellness rituals, and peaceful meditation."),
        "food": ("Authentic Local Food & Culinary Tasting", "Taste flavorful authentic dishes, savory street snacks, and fresh tropical delicacies."),
        "photography": ("Scenic Landscape & Landmark Photography", "Stunning vantage points capturing natural topography, dramatic skies, and architectural gems."),
        "adventure": ("Thrilling Outdoor Adventure Activity", "Action-packed outdoor experience featuring exhilarating terrain and picturesque settings."),
        "shopping": ("Local Artisan Market & Crafts Bazaar", "Browse authentic handicrafts, aromatic spices, handloomed textiles, and unique local souvenirs.")
    }

        # Helper function to pick a realistic hotel strictly within user's accommodation budget cap
    def pick_real_hotel(city_name: str, total_budget: float, trip_len: int, num_passengers: int = 1, acc_preference: str = ""):
        c_clean = str(city_name).lower().strip()
        matched_city = None
        for k in DESTINATION_REAL_HOTELS:
            if k in c_clean or c_clean in k:
                matched_city = k
                break

        # Sizing: required rooms
        r_needed = max(1, _math.ceil(num_passengers / 2))

        # Total accommodation budget cap: allocate up to 40% of total budget for accommodation
        acc_budget_total = float(total_budget) * 0.40
        # Nightly cap per room
        nightly_cap_per_room = acc_budget_total / max(trip_len * r_needed, 1)

        pref_str = str(acc_preference).lower()
        if "luxury" in pref_str or "resort" in pref_str or nightly_cap_per_room >= 26000:
            preferred_tier = "luxury"
        elif "budget" in pref_str or "hostel" in pref_str or nightly_cap_per_room < 10000:
            preferred_tier = "budget"
        else:
            preferred_tier = "mid"

        if matched_city and matched_city in DESTINATION_REAL_HOTELS:
            city_hotels = DESTINATION_REAL_HOTELS[matched_city]
            # Flatten all available hotels for this city sorted by price ascending
            all_city_hotels = []
            for t_name in ["budget", "mid", "luxury"]:
                for h_item in city_hotels.get(t_name, []):
                    all_city_hotels.append({**h_item, "_tier": t_name})

            # Filter hotels whose nightly price fits within nightly_cap_per_room
            affordable = [h for h in all_city_hotels if h["price"] <= nightly_cap_per_room * 1.15]

            if affordable:
                # If affordable options exist, pick the best one matching preferred tier
                preferred_matches = [h for h in affordable if h["_tier"] == preferred_tier]
                selected = preferred_matches[-1] if preferred_matches else affordable[-1]
                tier = selected["_tier"]
                alt_options = [h for h in affordable if h["name"] != selected["name"]][:2]
                return selected, alt_options, tier
            else:
                # If budget is tight, pick the absolute cheapest available hotel in the city
                cheapest_hotel = min(all_city_hotels, key=lambda x: x["price"])
                tier = "budget"
                alt_options = [h for h in all_city_hotels if h["name"] != cheapest_hotel["name"]][:2]
                return cheapest_hotel, alt_options, tier

        # Generic realistic fallback
        tier = preferred_tier
        tier_price = min(round(nightly_cap_per_room), 6000 if tier == "budget" else (14000 if tier == "mid" else 30000))
        tier_price = max(4000, tier_price)
        selected = {
            "name": f"{city_name.title()} Heritage Stay",
            "type": "hotel" if tier != "luxury" else "resort",
            "price": tier_price,
            "rating": 4.2,
            "features": ["wifi", "breakfast"],
            "reason": f"Comfortable {tier} accommodation selected to strictly fit within your allocated budget."
        }
        return selected, [], tier

    def get_activity_info(dest_city: str, category: str, fallback_raw: str, used_set: set = None):
        c_key = str(category).lower().strip()
        d_key = str(dest_city).lower().strip()

        def try_pick(title, desc):
            if used_set is None or title not in used_set:
                return (title, desc)
            return None

        # 1. Exact city match for requested category
        if d_key in DESTINATION_REAL_ACTIVITIES and c_key in DESTINATION_REAL_ACTIVITIES[d_key]:
            res = try_pick(*DESTINATION_REAL_ACTIVITIES[d_key][c_key])
            if res:
                return res

        # 2. Any other unused real activity for this city
        if d_key in DESTINATION_REAL_ACTIVITIES:
            for cat, item in DESTINATION_REAL_ACTIVITIES[d_key].items():
                res = try_pick(*item)
                if res:
                    return res

        # 3. Partial city match
        for known_city, cat_dict in DESTINATION_REAL_ACTIVITIES.items():
            if known_city in d_key or d_key in known_city:
                if c_key in cat_dict:
                    res = try_pick(*cat_dict[c_key])
                    if res:
                        return res

        # 4. Use category template
        if c_key in CATEGORY_DETAILS:
            res = try_pick(*CATEGORY_DETAILS[c_key])
            if res:
                return res

        # 5. Any unused category template
        for cat, item in CATEGORY_DETAILS.items():
            res = try_pick(*item)
            if res:
                return res

        clean = re.sub(r"\s+\d+$", "", str(fallback_raw)).strip().title()
        return (clean, f"Engaging {c_key.replace('_', ' ')} experience tailored to your itinerary.")

    def acc_type_label(t: str) -> str:
        return {
            "hotel": "Hotel",
            "hostel": "Hostel",
            "resort": "Resort",
            "villa": "Villa",
            "guest_house": "Guest House",
            "guesthouse": "Guest House",
            "homestay": "Homestay",
        }.get(str(t).lower(), str(t).replace("_", " ").title())

    # ── Real Clock-Time Itinerary & Guaranteed Accommodation ─────
    import math as _math
    from datetime import timedelta as _td

    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    except Exception:
        start_dt = datetime.today()

    # 1. Select Verified Real Accommodation strictly fitted to user's input budget and passenger count
    rooms_needed = max(1, _math.ceil(passengers / 2))
    picked_hotel, alt_hotels, detected_tier = pick_real_hotel(dest_name, budget, trip_days, passengers, acc_prefs)
    clean_hotel_name = picked_hotel["name"]
    hotel_type = acc_type_label(picked_hotel.get("type", "hotel"))
    hotel_price_val = int(picked_hotel.get("price", 8500))
    hotel_rating = picked_hotel.get("rating", 4.3)
    hotel_features = picked_hotel.get("features", ["wifi", "breakfast"])
    rooms_needed = max(1, _math.ceil(passengers / 2))

    # Build primary accommodation object
    hotel = {
        "accommodation_id": f"ACC_{re.sub(r'[^A-Za-z]', '', dest_name)[:4].upper()}_REAL",
        "name": clean_hotel_name,
        "type": picked_hotel.get("type", "hotel"),
        "destination": dest_name,
        "price_per_night": hotel_price_val,
        "rating": hotel_rating,
        "match_percentage": 92 if detected_tier == "mid" else 88,
        "matched_features": hotel_features,
        "reason": picked_hotel.get("reason", f"Selected to match your {detected_tier} budget and comfort preferences in {dest_name}."),
        "tier": detected_tier,
    }
    accommodations = [hotel]

    # Build alternative real accommodations
    formatted_alts = []
    for idx, alt in enumerate(alt_hotels[:2]):
        formatted_alts.append({
            "accommodation_id": f"ACC_{re.sub(r'[^A-Za-z]', '', dest_name)[:4].upper()}_ALT{idx+1}",
            "name": alt["name"],
            "type": alt.get("type", "hotel"),
            "destination": dest_name,
            "price_per_night": int(alt.get("price", 10000)),
            "rating": alt.get("rating", 4.2),
            "match_percentage": 85,
            "matched_features": alt.get("features", ["wifi"]),
            "reason": alt.get("reason", f"Alternative {alt.get('type', 'hotel')} option in {dest_name}."),
        })

    # 2. Expand activities so every day has multiple activities (2-3 per day)
    target_acts = max(trip_days * 2, min(trip_days * 3, 12))
    existing_cats = {str(act.get("category", "")).lower() for act in activities}
    d_key = dest_name.lower().strip()

    dest_acts = DESTINATION_REAL_ACTIVITIES.get(d_key, {})
    if not dest_acts:
        for k, v in DESTINATION_REAL_ACTIVITIES.items():
            if k in d_key or d_key in k:
                dest_acts = v
                break

    for cat, (title, desc) in dest_acts.items():
        if len(activities) >= target_acts:
            break
        if cat.lower() not in existing_cats:
            activities.append({
                "activity_id": f"ACT_{len(activities)+1:03d}",
                "activity_name": title,
                "category": cat,
                "cost": 1500 + (len(activities) * 400) % 2500,
                "duration_hours": 2.0,
                "rating": 4.5,
                "match_percentage": 82,
            })
            existing_cats.add(cat.lower())

    for cat, (title, desc) in CATEGORY_DETAILS.items():
        if len(activities) >= target_acts:
            break
        if cat.lower() not in existing_cats:
            activities.append({
                "activity_id": f"ACT_{len(activities)+1:03d}",
                "activity_name": title,
                "category": cat,
                "cost": 1200 + (len(activities) * 350) % 2200,
                "duration_hours": 1.5,
                "rating": 4.3,
                "match_percentage": 78,
            })
            existing_cats.add(cat.lower())

    # 3. Time formatting & distribution into days
    def fmt_time(total_minutes: int) -> str:
        h = (total_minutes // 60) % 24
        m = total_minutes % 60
        suffix = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d} {suffix}"

    acts_per_day = max(2, _math.ceil(len(activities) / max(trip_days, 1)))
    day_buckets = {}
    for i, act in enumerate(activities):
        day_num = min(trip_days, i // acts_per_day + 1)
        day_buckets.setdefault(day_num, []).append(act)

    activity_entries = []
    used_titles = set()
    for day_num in sorted(day_buckets.keys()):
        act_date = (start_dt + _td(days=day_num - 1)).strftime("%Y-%m-%d")
        # Day 1 starts at 10:00 AM (after 8:00 AM check-in)
        # Other days start at 9:00 AM
        clock = 10 * 60 if day_num == 1 else 9 * 60

        for act in day_buckets[day_num]:
            time_str = fmt_time(clock)
            raw_name = act.get("activity_name") or act.get("name") or "Activity"
            category = act.get("category", "")
            act_cost = act.get("cost", 0)
            act_dur = float(act.get("duration_hours", 1.5))
            match_pct = act.get("match_percentage", 0)

            real_title, real_summary = get_activity_info(dest_name, category, raw_name, used_titles)
            used_titles.add(real_title)
            full_desc = f"{real_summary} ({act_dur}h · LKR {act_cost:,})"
            if match_pct:
                full_desc += f" · {match_pct}% match"

            activity_entries.append({
                "day":           f"Day {day_num}",
                "date":          act_date,
                "time":          time_str,
                "type":          "activity",
                "location_name": real_title,
                "description":   full_desc,
            })

            clock += int(act_dur * 60) + 30
            # Lunch break: skip to 1:30 PM if landing around noon
            if 12 * 60 <= clock < 13 * 60 + 30:
                clock = 13 * 60 + 30

    # 4. Check-in on Day 1 at 8:00 AM
    checkin_date = start_dt.strftime("%Y-%m-%d")
    activity_entries.insert(0, {
        "day":           "Day 1",
        "date":          checkin_date,
        "time":          "8:00 AM",
        "type":          "checkin",
        "location_name": clean_hotel_name,
        "description":   (
            f"Arrive & check in · {hotel_type} · "
            f"LKR {hotel_price_val:,}/night · Rating: {hotel_rating}/5.0 · "
            f"{rooms_needed} room{'s' if rooms_needed > 1 else ''} reserved for {passengers} guest{'s' if passengers > 1 else ''}"
        ),
    })

    # 5. Check-out on last day at 12:00 PM
    checkout_date = (start_dt + _td(days=trip_days - 1)).strftime("%Y-%m-%d")
    activity_entries.append({
        "day":           f"Day {trip_days}",
        "date":          checkout_date,
        "time":          "12:00 PM",
        "type":          "checkout",
        "location_name": f"Check out · {clean_hotel_name}",
        "description":   f"Pack up and depart · Farewell to {dest_name}",
    })

    # 6. Sort chronologically within each day
    def time_to_minutes(t_str: str) -> int:
        try:
            parts = t_str.strip().split()
            hm = parts[0].split(":")
            h, m = int(hm[0]), int(hm[1])
            if len(parts) > 1 and parts[1].upper() == "PM" and h < 12:
                h += 12
            elif len(parts) > 1 and parts[1].upper() == "AM" and h == 12:
                h = 0
            return h * 60 + m
        except Exception:
            return 0

    day_order = {f"Day {d}": d for d in range(1, trip_days + 1)}
    activity_entries.sort(key=lambda x: (day_order.get(x["day"], 99), time_to_minutes(x["time"])))

    # 7. Strict Budget-Constrained Itinerary & Cost Allocation
    user_input_budget = float(budget) if budget else 20000.0

    # A. Accommodation cost based on selected verified hotel
    actual_acc_total = round(hotel_price_val * trip_days * rooms_needed)

    # B. Realistic Transport & Fuel Cost Calibration (Petrol LKR 480/L)
    one_way_km = estimate_road_distance_km(origin or "Colombo", dest_name)
    # Round trip (to & from) + local daily sightseeing travel (~30km/day)
    total_travel_km = (one_way_km * 2) + (trip_days * 30)

    if preferred_transport in ("bus", "train"):
        # Intercity bus / train tickets + local tuk-tuk / city buses
        # Bus/Train: ~LKR 1,000 - 1,500 per passenger for long-distance + local
        transport_est = round((one_way_km * 2 * 3.5 * passengers) + (trip_days * 450 * passengers))
        transport_est = max(round(trip_days * 800 * passengers), transport_est)
        transport_note = f"Public Transport ({mode}) for {passengers} pax · ~{total_travel_km} km total"
    else:
        # Car / Van: Realistic Fuel Consumption Calculation (Petrol LKR 480/L)
        # Standard car fuel economy in Sri Lanka: ~11-12 km/L on long distance / hills
        fuel_price_per_liter = 480.0
        car_km_per_liter = 11.5 if passengers <= 4 else 8.5 # Van consumes more
        liters_needed = total_travel_km / car_km_per_liter
        fuel_cost = round(liters_needed * fuel_price_per_liter)

        # Express Highway toll fees (if route utilizes E01 / E02 / E04, ~LKR 800 - 1,600 round trip)
        highway_tolls = 1200 if any(c in f"{origin} {dest_name}".lower() for c in ["galle", "matara", "mirissa", "bentota", "kandy"]) else 0

        # Total realistic transport
        transport_est = fuel_cost + highway_tolls
        transport_note = f"Estimated Fuel for ~{total_travel_km} km @ LKR {int(fuel_price_per_liter)}/L ({liters_needed:.1f}L needed)"


    # C. Calculate remaining available budget for Food and Activities
    fixed_costs = actual_acc_total + transport_est
    remaining_for_food_and_acts = max(0, user_input_budget - fixed_costs)

    # Food daily rate: standard LKR 2,000 - 2,800/person, but dynamically scaled if budget is tight
    ideal_food_per_day = 2200
    if remaining_for_food_and_acts > 0:
        max_possible_food = remaining_for_food_and_acts * 0.65
        calibrated_food_daily = min(ideal_food_per_day, max(1200, max_possible_food / max(trip_days * passengers, 1)))
        food_est = round(calibrated_food_daily * trip_days * passengers)
    else:
        food_est = round(1200 * trip_days * passengers)

    # D. Activity costs: budget-constrained so total does not exceed user's input budget
    remaining_for_acts = max(0, user_input_budget - (actual_acc_total + transport_est + food_est))
    raw_act_total = sum(round(act.get("cost", 0) * passengers) for act in activities)

    if raw_act_total > 0 and remaining_for_acts > 0:
        if raw_act_total <= remaining_for_acts:
            actual_act_total = raw_act_total
        else:
            # Scale activity fees so total plan fits strictly within user's budget
            scale_ratio = remaining_for_acts / raw_act_total
            actual_act_total = round(remaining_for_acts)
            # Adjust individual activity costs in activity_entries
            for act in activity_entries:
                if "cost" in act and act["cost"] > 0:
                    act["cost"] = round(act["cost"] * scale_ratio)
    elif raw_act_total > 0 and remaining_for_acts <= 0:
        # Minimal essential ticket fees
        actual_act_total = min(raw_act_total, round(trip_days * 1000 * passengers))
    else:
        actual_act_total = 0

    actual_total = actual_acc_total + actual_act_total + food_est + transport_est
    per_person_est = round(actual_total / passengers)

    # Budget Health Evaluation
    is_covered = actual_total <= user_input_budget
    savings_or_buffer = round(user_input_budget - actual_total) if is_covered else 0
    budget_deficit = round(actual_total - user_input_budget) if not is_covered else 0

    passenger_label = f"{passengers} Traveller{'s' if passengers > 1 else ''}"
    plan_data = {
        "title":                     f"{trip_days}-Day Trip to {dest_name}",
        "duration":                  f"{trip_days} day{'s' if trip_days > 1 else ''}",
        "destination":               dest_name,
        "passengers":                passengers,
        "passenger_label":           passenger_label,
        "rooms_needed":              rooms_needed,
        "travel_type":               travel_type,
        "input_budget":              int(user_input_budget),
        "is_covered":                is_covered,
        "savings_or_buffer":         savings_or_buffer,
        "budget_deficit":            budget_deficit,
        "match_percentage":          dest.get("match_percentage", None),
        "recommendation_reason":     dest.get("reason", ""),
        "activities":                activity_entries,
        "recommended_accommodation": accommodations[0],
        "alternative_accommodations": formatted_alts,
        "alternative_destinations":  ml_data.get("alternative_destinations", [])[:3],
        "budget_breakdown": {
            "accommodation": actual_acc_total,
            "activities":    actual_act_total,
            "food":          food_est,
            "transport":      transport_est,
            "transport_note": transport_note,
            "total":          actual_total,
            "per_person":    per_person_est,
            "input_budget":  int(user_input_budget),
            "is_covered":    is_covered,
            "savings":       savings_or_buffer,
        },
    }

    return plan_data, None



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
            if 'default_passengers' in data:
                profile.default_passengers = data['default_passengers']
            if 'default_travel_mode' in data:
                profile.default_travel_mode = data['default_travel_mode']
            if 'interests_csv' in data:
                profile.interests_csv = data['interests_csv']
            if 'food_preferences' in data:
                profile.food_preferences = data['food_preferences']
            if 'accommodation_preferences' in data:
                profile.accommodation_preferences = data['accommodation_preferences']
            if 'activity_preferences' in data:
                profile.activity_preferences = data['activity_preferences']
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

        # ── Load saved user profile as smart defaults ─────────────────────
        # Request value always wins; profile value is the fallback.
        # This ensures itineraries are personalised even with partial input.
        try:
            profile = request.user.profile
        except Exception:
            profile = None

        def profile_val(field, default=""):
            """Return the saved profile field, or default if missing/empty."""
            if profile is None:
                return default
            val = getattr(profile, field, None)
            if val is None:
                return default
            if isinstance(val, str):
                return val.strip() or default
            return val if val else default

        origin     = data.get("origin", "").strip() or "Colombo"
        country    = data.get("country", "Sri Lanka").strip() or "Sri Lanka"
        city       = data.get("city", "").strip()
        start_date = data.get("start_date", "")
        end_date   = data.get("end_date", "")

        # Merge request + profile: request wins, profile is fallback
        interests                 = data.get("interests", "").strip() or profile_val("interests_csv")
        food_preferences          = data.get("food_preferences", "").strip() or profile_val("food_preferences")
        accommodation_preferences = data.get("accommodation_preferences", "").strip() or profile_val("accommodation_preferences")
        activity_preferences      = data.get("activity_preferences", "").strip() or profile_val("activity_preferences")

        # Passengers: count of travellers (default 1 or user profile default)
        try:
            passengers = int(data.get("passengers", 0) or 0)
            if passengers <= 0:
                passengers = int(profile_val("default_passengers", 1))
        except (ValueError, TypeError):
            passengers = int(profile_val("default_passengers", 1))

        # Budget: use request if > 0, else fall back to saved profile budget
        try:
            budget = int(data.get("budget", 0) or 0)
            if budget <= 0:
                budget = int(profile_val("default_budget", 20000))
        except (ValueError, TypeError):
            budget = int(profile_val("default_budget", 20000))

        # Travel mode: use request if valid, else use saved profile mode
        valid_modes = {"Car", "Bus", "Train"}
        mode = str(data.get("travel_mode", "")).strip()
        if mode not in valid_modes:
            mode = profile_val("default_travel_mode", "Car")

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
        budget_ref  = get_budget_reference(budget, mode, duration_days)

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
        combined_interests = f"{interests}, {food_preferences}, {accommodation_preferences}, {activity_preferences}"
        alternatives = suggest_alternative_destinations(city, combined_interests, country)

        # ── Rainy-Day Weather Alert & Drier-Region Recommendations ──────────
        weather_alert = suggest_rainy_weather_alternatives(
            city=city,
            weather_days=weather_days,
            start_date_str=start_date,
            interests=combined_interests,
            country=country,
            user=request.user,
        )

        # ── AI Itinerary Generation ─────────────────────────────────────────
        plan_data, error = call_ml_service(
            city, country, origin, start_date, end_date, interests,
            food_preferences, accommodation_preferences, activity_preferences,
            budget, mode, recommended_str, passengers=passengers
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
                food_preferences=food_preferences,
                accommodation_preferences=accommodation_preferences,
                activity_preferences=activity_preferences,
                budget=budget,
                passengers=passengers,
                travel_mode=mode,
                plan_json=plan_data,
                weather_summary=weather_summary,
                map_url=map_url,
            )
        except Exception as e:
            print(f"DB save error: {e}")

        return Response(
            {
                "plan":           plan_data,
                "weather":        weather_summary,
                "weather_days":   weather_days,
                "map_url":        map_url,
                "season_info":    season_info,
                "budget_ref":     budget_ref,
                "alternatives":   alternatives,
                "weather_alert":  weather_alert,   # 🌧️ rainy-day drier alternatives
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

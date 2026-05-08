import os
import json
import re
import requests
from datetime import datetime

from django.contrib.auth.models import User
from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_groq import ChatGroq
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Destination, TripPlan
from .serializers import (
    DestinationSerializer,
    RegisterSerializer,
    TripPlanSerializer,
    UserSerializer,
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

# ── 4. Helper functions ───────────────────────────────────────────────────────

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


def get_weather_forecast(city: str, country: str, start_date_str: str) -> str:
    if not OPENWEATHER_API_KEY:
        return "Weather API key not configured."

    search_query = f"{city},{country}" if country else city
    lat, lon = get_coordinates(search_query)
    if lat is None:
        lat, lon = get_coordinates(city)
    if lat is None:
        return f"Coordinates not found for {city}."

    try:
        url = (
            f"http://api.openweathermap.org/data/2.5/forecast"
            f"?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        )
        data = requests.get(url, timeout=5).json()
        target_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

        for item in data.get("list", []):
            forecast_time = datetime.fromtimestamp(item["dt"])
            if forecast_time.date() == target_date and 9 <= forecast_time.hour <= 15:
                desc = item["weather"][0]["description"].capitalize()
                temp = item["main"]["temp"]
                humidity = item["main"]["humidity"]
                pop = item.get("pop", 0) * 100
                return f"{desc}, {temp}°C, Humidity {humidity}%, Rain {pop:.0f}%"

        return "Forecast unavailable for this date."
    except Exception as e:
        print(f"Weather error: {e}")
        return "Weather service temporarily unavailable."


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
        profile = request.user.profile
        data = request.data
        if 'default_budget' in data:
            profile.default_budget = int(data['default_budget'])
        if 'default_travel_mode' in data:
            profile.default_travel_mode = data['default_travel_mode']
        if 'interests_csv' in data:
            profile.interests_csv = data['interests_csv']
        profile.save()
        return Response(UserSerializer(request.user).data)


# ── 6. Planner Views ──────────────────────────────────────────────────────────

class TravelPlanView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        origin = data.get("origin", "").strip()
        country = data.get("country", "Sri Lanka").strip()
        city = data.get("city", "").strip()
        start_date = data.get("start_date", "")
        end_date = data.get("end_date", "")
        interests = data.get("interests", "")
        budget = data.get("budget", 0)
        mode = data.get("travel_mode", "Car")

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
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        # Weather
        weather = get_weather_forecast(city, country, start_date)

        # Algorithmic Pre-filter based on interests
        recommended = []
        if interests:
            interest_list = [i.strip().lower() for i in interests.split(',')]
            dests = Destination.objects.filter(country__icontains=country)
            for d in dests:
                if d.category.lower() in interest_list:
                    recommended.append(d.name)
        
        recommended_str = ", ".join(recommended[:5])

        # AI generation
        plan_data, error = generate_itinerary(
            city, country, origin, start_date, end_date, interests, budget, mode, recommended_str
        )
        if plan_data is None:
            return Response({"error": error}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # Build Google Maps URL
        path_parts = [origin.replace(" ", "+") if origin else country.replace(" ", "+")]
        for act in plan_data.get("activities", [])[:9]:
            path_parts.append(act.get("location_name", "").replace(" ", "+"))
        map_url = "https://www.google.com/maps/dir/" + "/".join(filter(None, path_parts))

        # Save to DB
        try:
            TripPlan.objects.create(
                user=request.user,
                origin=origin,
                destination_city=city,
                destination_country=country,
                start_date=start_date,
                end_date=end_date,
                interests=interests,
                budget=int(budget),
                travel_mode=mode,
                plan_json=plan_data,
                weather_summary=weather,
                map_url=map_url,
            )
        except Exception as e:
            print(f"DB save error: {e}")  # Don't fail the response if save fails

        return Response(
            {"plan": plan_data, "weather": weather, "map_url": map_url},
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

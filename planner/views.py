from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os
import json
import re
import requests
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

# 1. Load Keys
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

# --- Helper Functions ---

CITY_BACKUP = {
    "colombo": {"lat": 6.9271, "lon": 79.8612},
    "kandy": {"lat": 7.2906, "lon": 80.6337},
    "galle": {"lat": 6.0535, "lon": 80.2210},
    "matara": {"lat": 5.9549, "lon": 80.5550},
    "tangalle": {"lat": 6.0244, "lon": 80.7941},
    "dikwella": {"lat": 5.9660, "lon": 80.6976},
    "kataragama": {"lat": 6.4135, "lon": 81.3325},
    "nuwara eliya": {"lat": 6.9497, "lon": 80.7891},
    "london": {"lat": 51.5074, "lon": -0.1278}
}

def get_coordinates(city_name):
    city_clean = city_name.lower().strip()
    if city_clean in CITY_BACKUP:
        return CITY_BACKUP[city_clean]['lat'], CITY_BACKUP[city_clean]['lon']
    
    if OPENWEATHER_API_KEY:
        try:
            url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={OPENWEATHER_API_KEY}"
            res = requests.get(url)
            if res.status_code == 200 and res.json():
                data = res.json()[0]
                return data['lat'], data['lon']
        except:
            pass
    return None, None

def get_weather_forecast(city, country, start_date_str):
    if not OPENWEATHER_API_KEY:
        return "Weather API Key missing."
    
    search_query = f"{city},{country}" if country else city
    lat, lon = get_coordinates(search_query)
    if not lat:
        lat, lon = get_coordinates(city) 
        
    if not lat:
        return "Coordinates not found."

    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        data = requests.get(url).json()
        
        target_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        
        for item in data['list']:
            forecast_time = datetime.fromtimestamp(item['dt'])
            if forecast_time.date() == target_date:
                if 9 <= forecast_time.hour <= 15:
                    desc = item['weather'][0]['description'].capitalize()
                    temp = item['main']['temp']
                    return f"{desc}, {temp}°C"
        return "Forecast unavailable for date."
    except:
        return "Weather service error."

# --- The API View ---

class TravelPlanView(APIView):
    def post(self, request):
        # 1. Get Data
        data = request.data
        origin = data.get('origin', '')
        country = data.get('country', '')
        city = data.get('city', '')
        start_date = data.get('start_date', '')
        end_date = data.get('end_date', '')
        interests = data.get('interests', '')
        budget = data.get('budget', 0)
        mode = data.get('travel_mode', 'Car')

        # 2. Weather
        weather = get_weather_forecast(city, country, start_date)

        # 3. AI Generation
        llm = ChatGroq(temperature=0.1, groq_api_key=GROQ_API_KEY, model_name="llama-3.3-70b-versatile")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Generate a JSON trip plan. Keys: title, duration, activities (list with day, time, location_name, description), budget_breakdown. NO TRAINS to Kataragama/Hambantota."),
            ("human", f"Trip to {city}, {country} from {origin}. Dates: {start_date}-{end_date}. Interests: {interests}. Budget: {budget}. Mode: {mode}")
        ])
        
        try:
            response = llm.invoke(prompt.format_messages())
            clean_json = re.search(r"\{.*\}", response.content, re.DOTALL).group(0)
            plan_data = json.loads(clean_json)
        except Exception as e:
            # Fallback if AI fails
            plan_data = {"title": "Error generating plan", "activities": []}

        # 4. Map Link Logic
        map_path = [origin] if origin else []
        dest_locs = [act['location_name'] for act in plan_data.get('activities', [])]
        map_path.extend(dest_locs[:9])
        waypoints = "/".join([loc.replace(" ", "+") for loc in map_path])
        map_url = f"https://www.google.com/maps/dir/{waypoints}"

        return Response({
            "plan": plan_data,
            "weather": weather,
            "map_url": map_url
        }, status=status.HTTP_200_OK)
import os
import json
import re
import requests
import time
import gradio as gr 
from datetime import datetime, timedelta
from dotenv import load_dotenv
from typing import TypedDict, Annotated, List, Dict, Any
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

# --- 1. CONFIGURATION ---
load_dotenv() 

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY") 

if not GROQ_API_KEY:
    raise ValueError("❌ Error: GROQ_API_KEY is missing in .env file!")

# Backup Coordinates
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
    "london": {"lat": 51.5074, "lon": -0.1278}
}

# Initialize LLM
llm = ChatGroq(
    temperature=0.1,
    groq_api_key=GROQ_API_KEY,
    model_name="llama-3.3-70b-versatile"
)

# --- 2. HELPER FUNCTIONS ---

def get_coordinates(city_name: str):
    city_clean = city_name.lower().strip()
    if city_clean in CITY_BACKUP:
        return CITY_BACKUP[city_clean]['lat'], CITY_BACKUP[city_clean]['lon']
    
    if OPENWEATHER_API_KEY:
        try:
            url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={OPENWEATHER_API_KEY}"
            response = requests.get(url)
            if response.status_code == 200 and response.json():
                data = response.json()[0]
                return data['lat'], data['lon']
        except Exception as e:
            print(f"Geo API Error: {e}") 
    return None, None

def get_weather_forecast(city: str, country: str, start_date_str: str) -> str:
    if not OPENWEATHER_API_KEY:
        return "⚠️ Weather API Key not found."

    search_query = f"{city},{country}" if country else city
    lat, lon = get_coordinates(search_query)
    
    if lat is None:
        lat, lon = get_coordinates(city)

    if lat is None:
        return f"Could not find coordinates for <b>{city}</b>."

    try:
        url = f"http://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url)
        data = response.json()

        try:
            # Calendar sends string, ensure format
            target_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except ValueError:
            return "Invalid date format."

        today = datetime.now().date()
        if target_date < today:
            return "Start date is in the past."
        if (target_date - today).days > 5:
            return f"📅 Note: Precise forecast is only available for the next 5 days."

        for item in data['list']:
            forecast_time = datetime.fromtimestamp(item['dt'])
            if forecast_time.date() == target_date:
                if 9 <= forecast_time.hour <= 15:
                    desc = item['weather'][0]['description'].capitalize()
                    temp = item['main']['temp']
                    humidity = item['main']['humidity']
                    wind = item['wind']['speed']
                    pop = item.get('pop', 0) * 100
                    
                    icon = "🌧" if pop > 50 else "⛅" if pop > 20 else "☀️"

                    return (
                        f"<b>{icon} Forecast for {target_date}:</b> {desc}<br>"
                        f"🌡 Temp: {temp}°C | 💧 Humidity: {humidity}% | ☔ Rain Chance: {pop:.0f}%"
                    )
        
        return "Weather data not found for this specific date."

    except Exception as e:
        print(f"Weather Logic Error: {e}")
        return "Weather data temporarily unavailable."

# --- 3. AI PROMPT ---

itinerary_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert travel guide for Sri Lanka. "
     "Create a realistic trip plan. "
     "IMPORTANT RULES FOR SRI LANKA: \n"
     "1. There are NO TRAINS to Kataragama, Hambantota, Embilipitiya, or Monaragala. Use Bus or Taxi. \n"
     "2. Trains only run up to Beliatta in the South. \n"
     "STRICT JSON OUTPUT ONLY: \n"
     "Structure: {{'title': '...', 'duration': '...', 'activities': [{{'day': '...', 'time': '...', 'location_name': '...', 'description': '...'}}], 'budget_breakdown': {{...}} }} \n"
     " 'location_name' must be a real place name recognizable by Google Maps."),
    ("human",
     "Plan a trip to: {city}, {country}\nStarting From: {origin}\nDates: {start_date} to {end_date}\nInterests: {interests}\nBudget: {budget} LKR\nPreferred Mode: {travel_mode}")
])

def generate_plan_with_retry(prompt_input, max_retries=2):
    for attempt in range(max_retries):
        try:
            print(f"⏳ AI request attempt {attempt+1}...")
            response = llm.invoke(prompt_input)
            content = response.content
            clean_content = re.sub(r'```json', '', content).replace('```', '').strip()
            match = re.search(r"\{.*\}", clean_content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                print("⚠️ Invalid JSON format received. Retrying...") 
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(1)
    return None

# --- 4. MAIN LOGIC (WITH CALENDAR HANDLING) ---

def main_planner(origin, country, city, start_date, end_date, interests, budget, travel_mode):
    # Safety Check: Did user select dates?
    if not start_date or not end_date:
        return "<h3>⚠️ Error</h3><p>Please select both Start Date and End Date from the calendar.</p>"

    # CLEANING: Calendar might return '2025-12-20 00:00:00', we need just '2025-12-20'
    start_date = str(start_date).split(' ')[0]
    end_date = str(end_date).split(' ')[0]
    
    origin = origin.strip()
    country = country.strip()
    city = city.strip()
    
    weather_report = get_weather_forecast(city, country, start_date)
    
    prompt_input = itinerary_prompt.format_messages(
        city=city, country=country, origin=origin, 
        start_date=start_date, end_date=end_date,
        interests=interests, budget=budget, travel_mode=travel_mode
    )
    
    data = generate_plan_with_retry(prompt_input)
    
    if not data:
        return "<h3>⚠️ System Error</h3><p>AI could not generate a valid plan.</p>"

    # Map Logic
    map_path = [origin] if origin else []
    dest_locations = [act['location_name'] for act in data.get('activities', [])]
    map_path.extend(dest_locations[:9])
    waypoints_str = "/".join([loc.replace(" ", "+") for loc in map_path])
    
    if not waypoints_str:
        map_url = f"https://www.google.com/maps/dir/{city}"
    else:
        map_url = f"https://www.google.com/maps/dir/{waypoints_str}"

    # HTML Output (High Contrast + White Background)
    html = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; background-color: #ffffff !important; color: #000000 !important; padding: 25px; border-radius: 12px; border: 2px solid #ccc; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
        
        <h1 style="color: #000000 !important; border-bottom: 3px solid #007bff; padding-bottom: 10px; margin-top: 0;">{data.get('title', 'Trip Plan')}</h1>
        
        <p style="font-size: 1.2em; color: #000000 !important;"><b>🚗 Trip:</b> {origin} ➡️ {city}, {country}</p>
        <p style="font-size: 1.1em; color: #000000 !important;"><b>🗓 Duration:</b> {start_date} to {end_date}</p>
        
        <div style="background-color: #e3f2fd !important; padding: 15px; border-radius: 8px; border-left: 6px solid #2196f3; margin: 20px 0; color: #000000 !important;">
            <h3 style="margin-top:0; color: #0d47a1 !important;">🌦 Weather Forecast</h3>
            {weather_report}
        </div>

        <div style="margin: 25px 0; text-align: center;">
            <a href='{map_url}' target='_blank' style='display:inline-block; background-color: #28a745 !important; color: #ffffff !important; padding: 14px 28px; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 1.2em; border: 1px solid #1e7e34;'>
                📍 View Route on Google Maps
            </a>
            <p style="font-size: 0.9em; color: #333333 !important; margin-top: 8px;">(Click to see traffic & shortest path)</p>
        </div>

        <hr style="border-top: 2px solid #bbb;">

        <h3 style="color: #000000 !important; text-decoration: underline;">📅 Daily Itinerary</h3>
    """
    
    for activity in data.get('activities', []):
        html += f"""
        <div style="margin-bottom: 20px; padding: 15px; background-color: #f8f9fa !important; border: 1px solid #ddd; border-radius: 8px;">
            <div style="background-color: #343a40 !important; color: #ffffff !important; display: inline-block; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 0.9em; margin-bottom: 8px;">
                {activity.get('day', 'Day')} - {activity.get('time', '')}
            </div>
            <div style="color: #000000 !important;">
                <b style="color: #d63384 !important;">📍 {activity.get('location_name', '')}</b>: {activity.get('description', '')}
            </div>
        </div>
        """
        
    html += """
        <hr style='border-top: 2px solid #bbb;'>
        <h3 style='color: #000000 !important; text-decoration: underline;'>💰 Estimated Budget</h3>
        <ul style='list-style-type: none; padding: 0; color: #000000 !important;'>
    """
    
    for item, cost in data.get('budget_breakdown', {}).items():
        html += f"<li style='padding: 8px 0; border-bottom: 1px dashed #ccc; color: #000000 !important;'><b>{item}:</b> {cost} LKR</li>"
    html += "</ul></div>"

    return html

# --- GRADIO UI (UPDATED WITH CALENDAR) ---

if __name__ == "__main__":
    ui = gr.Interface(
        fn=main_planner,
        inputs=[
            gr.Textbox(label="Starting From (Origin)", placeholder="e.g. Colombo"),
            gr.Textbox(label="Destination Country", placeholder="e.g. Sri Lanka"),
            gr.Textbox(label="Destination City", placeholder="e.g. Kataragama"),
            # --- CALENDAR COMPONENTS ---
            gr.DateTime(label="Start Date", include_time=False, type="string"),
            gr.DateTime(label="End Date", include_time=False, type="string"),
            # ---------------------------
            gr.Textbox(label="Interests", placeholder="Culture, Temples"),
            gr.Number(label="Budget (LKR)", value=20000),
            gr.Radio(["Car", "Bus", "Train"], label="Preferred Mode", value="Car")
        ],
        outputs=gr.HTML(label="Your Personal Travel Plan"),
        title="🌍 Travemle - AI Smart Travel Planner",
        description="Plan your trip with accurate routes, weather, and calendar picking.",
        theme=gr.themes.Soft(),
        allow_flagging="never"
    )
    
    ui.launch()
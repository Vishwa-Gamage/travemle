import requests
import json

# අපේ Django API Link එක
url = 'http://127.0.0.1:8000/api/plan-trip/'

# අපි API එකට යවන දත්ත (හරියට Mobile App එකෙන් යවනවා වගේ)
payload = {
    "origin": "Colombo",
    "country": "Sri Lanka",
    "city": "Kandy",
    "start_date": "2025-12-20",
    "end_date": "2025-12-22",
    "interests": "Temple, Nature",
    "budget": 20000,
    "travel_mode": "Car"
}

print("⏳ Sending request to Django API...")

try:
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        print("\n✅ Success! API Response:")
        # ලස්සනට JSON එක පෙන්වන්න
        print(json.dumps(response.json(), indent=4))
    else:
        print(f"\n❌ Error: {response.status_code}")
        print(response.text)

except Exception as e:
    print(f"\n❌ Connection Error: {e}")
    print("Make sure the Django server is running! (python manage.py runserver)")
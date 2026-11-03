"""Generate deterministic, clearly labelled demo catalogs for TRAVEMLE."""
from pathlib import Path
import csv
import random

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
random.seed(42)

DESTINATIONS = [
    ("Ella", "Badulla", "Uva", 6.8667, 81.0466, 18000, 2, 4, 0.92, .88, .95, .82, .05, .65, .35, .55, .20, .25, .60, "cool", "mountain"),
    ("Kandy", "Kandy", "Central", 7.2906, 80.6337, 16000, 2, 4, .90, .90, .72, .55, .10, .35, .50, .45, .35, .60, .55, "cool", "cultural"),
    ("Nuwara Eliya", "Nuwara Eliya", "Central", 6.9497, 80.7891, 17000, 2, 4, .88, .78, .75, .35, .05, .30, .35, .70, .20, .45, .40, "cool", "mountain"),
    ("Mirissa", "Matara", "Southern", 5.9483, 80.4716, 19000, 2, 4, .89, .84, .55, .20, .90, .45, .15, .50, .25, .45, .50, "tropical", "beach"),
    ("Galle", "Galle", "Southern", 6.0329, 80.2168, 20000, 2, 4, .91, .87, .40, .20, .72, .70, .20, .45, .55, .68, .55, "tropical", "cultural"),
    ("Sigiriya", "Matale", "Central", 7.9570, 80.7603, 15000, 1, 3, .93, .90, .58, .75, .05, .40, .70, .35, .25, .40, .45, "tropical", "historical"),
    ("Dambulla", "Matale", "Central", 7.8731, 80.7718, 13000, 1, 3, .86, .76, .45, .50, .05, .30, .80, .30, .30, .40, .42, "tropical", "historical"),
    ("Anuradhapura", "Anuradhapura", "North Central", 8.3114, 80.4037, 12000, 2, 4, .87, .80, .35, .25, .05, .20, .90, .25, .25, .35, .45, "dry", "historical"),
    ("Polonnaruwa", "Polonnaruwa", "North Central", 7.9403, 81.0188, 12000, 1, 3, .86, .77, .40, .30, .05, .25, .88, .25, .20, .35, .40, "dry", "historical"),
    ("Trincomalee", "Trincomalee", "Eastern", 8.5874, 81.2152, 17000, 2, 4, .90, .85, .60, .30, .92, .55, .25, .50, .30, .50, .55, "tropical", "beach"),
    ("Arugam Bay", "Ampara", "Eastern", 6.8400, 81.8360, 16000, 2, 4, .88, .82, .55, .95, .75, .35, .15, .45, .20, .40, .48, "tropical", "adventure"),
    ("Yala", "Hambantota", "Southern", 6.3728, 81.5185, 22000, 2, 4, .91, .86, .82, .72, .05, .95, .25, .40, .10, .42, .50, "dry", "wildlife"),
    ("Udawalawe", "Ratnapura", "Sabaragamuwa", 6.4750, 80.8880, 18000, 2, 3, .89, .80, .78, .55, .05, .92, .20, .35, .10, .40, .45, "tropical", "wildlife"),
    ("Bentota", "Galle", "Southern", 6.4210, 80.0000, 21000, 2, 4, .88, .86, .45, .65, .88, .35, .15, .55, .25, .58, .65, "tropical", "beach"),
    ("Hikkaduwa", "Galle", "Southern", 6.1395, 80.1463, 18000, 2, 4, .86, .84, .40, .72, .90, .40, .15, .60, .40, .60, .55, "tropical", "beach"),
    ("Negombo", "Gampaha", "Western", 7.2083, 79.8358, 15000, 1, 3, .82, .84, .35, .20, .85, .30, .10, .55, .65, .58, .55, "tropical", "beach"),
    ("Jaffna", "Jaffna", "Northern", 9.6615, 80.0255, 13000, 2, 4, .84, .72, .30, .15, .20, .20, .80, .30, .55, .45, .40, "dry", "cultural"),
    ("Kalpitiya", "Puttalam", "North Western", 8.2370, 79.7580, 16000, 2, 4, .85, .76, .70, .85, .78, .45, .12, .45, .15, .40, .45, "tropical", "adventure"),
    ("Haputale", "Badulla", "Uva", 6.7681, 80.9598, 14000, 1, 3, .87, .74, .80, .50, .05, .25, .25, .62, .15, .38, .35, "cool", "mountain"),
    ("Knuckles", "Kandy", "Central", 7.5000, 80.8000, 15000, 2, 4, .90, .70, .98, .90, .03, .45, .15, .30, .10, .30, .35, "cool", "adventure"),
    ("Kitulgala", "Kegalle", "Sabaragamuwa", 6.9890, 80.4170, 15500, 1, 3, .88, .73, .90, .98, .03, .30, .15, .30, .12, .35, .38, "tropical", "adventure"),
    ("Sinharaja", "Ratnapura", "Sabaragamuwa", 6.4000, 80.5000, 15000, 2, 4, .89, .70, .99, .70, .02, .78, .18, .25, .08, .25, .30, "tropical", "wildlife"),
    ("Horton Plains", "Nuwara Eliya", "Central", 6.8020, 80.7890, 16000, 1, 2, .91, .75, .97, .82, .02, .55, .15, .40, .08, .28, .32, "cool", "mountain"),
    ("Unawatuna", "Galle", "Southern", 6.0100, 80.2500, 19000, 2, 4, .88, .86, .45, .35, .94, .40, .15, .55, .35, .62, .60, "tropical", "beach"),
    ("Pasikuda", "Batticaloa", "Eastern", 7.9200, 81.5600, 20000, 2, 4, .90, .82, .40, .20, .98, .30, .12, .50, .15, .60, .72, "tropical", "beach"),
    ("Nilaveli", "Trincomalee", "Eastern", 8.6900, 81.1900, 19000, 2, 4, .91, .80, .40, .25, .97, .40, .15, .55, .15, .58, .65, "tropical", "beach"),
]
# Extend to 40 realistic demo entries by adding nearby variants.
for index in range(len(DESTINATIONS) + 1, 41):
    base = DESTINATIONS[(index - 1) % len(DESTINATIONS)]
    scores = [round(max(0, min(1, value + random.uniform(-.06, .06))), 2) for value in base[10:19]] + [.5]
    DESTINATIONS.append((f"Sri Lanka Demo {index:02d}", base[1], base[2], base[3] + random.uniform(-.2, .2), base[4] + random.uniform(-.2, .2), base[5] + random.randint(-2000, 2500), base[6], base[7], base[8], base[9], *scores, base[19], base[20]))

DEST_HEADERS = ["destination_id", "destination_name", "district", "province", "latitude", "longitude", "average_daily_cost", "recommended_min_days", "recommended_max_days", "rating", "popularity_score", "nature_score", "adventure_score", "culture_score", "beach_score", "wildlife_score", "wellness_score", "nightlife_score", "shopping_score", "family_score", "luxury_score", "climate", "destination_type", "description"]

def write_catalogs():
    DATA.mkdir(exist_ok=True)
    with (DATA / "destinations.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file); writer.writerow(DEST_HEADERS)
        for index, row in enumerate(DESTINATIONS, 1):
            if len(row) == 21:
                row = (*row[:19], .5, *row[19:])
            writer.writerow([f"DEST{index:03d}", *row, f"Demo destination profile for {row[0]}; values are illustrative and not official tourism statistics."])

    accommodation_headers = ["accommodation_id", "name", "destination_id", "destination_name", "accommodation_type", "price_per_night", "rating", "review_count", "wifi", "pool", "breakfast", "parking", "air_conditioning", "family_friendly", "accessible", "luxury_score", "budget_score", "latitude", "longitude"]
    types = ["hotel", "resort", "hostel", "guest_house", "villa", "homestay"]
    with (DATA / "accommodations.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file); writer.writerow(accommodation_headers)
        for index in range(120):
            destination_index = index % len(DESTINATIONS); destination = DESTINATIONS[destination_index]
            kind = types[index % len(types)]; price = round(destination[5] * (0.45 + (index % 7) * .13))
            writer.writerow([f"HOT{index + 1:03d}", f"{destination[0]} {kind.replace('_', ' ').title()} {index + 1}", f"DEST{destination_index + 1:03d}", destination[0], kind, price, round(3.7 + (index % 14) / 20, 1), 20 + index * 7, index % 5 != 0, index % 3 != 0, index % 4 != 0, index % 6 != 0, index % 4 != 1, index % 3 != 1, index % 7 != 0, round(.35 + (index % 8) / 12, 2), round(.45 + ((index + 3) % 8) / 12, 2), destination[3] + .001, destination[4] + .001])

    activity_headers = ["activity_id", "activity_name", "destination_id", "destination_name", "category", "cost", "duration_hours", "rating", "nature_score", "adventure_score", "culture_score", "beach_score", "wildlife_score", "wellness_score", "shopping_score", "family_score", "indoor", "outdoor", "family_friendly", "accessible", "latitude", "longitude", "description"]
    categories = ["hiking", "wildlife", "cultural", "historical", "beach", "water_sports", "sightseeing", "wellness", "food", "shopping", "adventure", "photography"]
    with (DATA / "activities.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file); writer.writerow(activity_headers)
        for index in range(180):
            destination_index = index % len(DESTINATIONS); destination = DESTINATIONS[destination_index]; category = categories[index % len(categories)]
            emphasis = {"nature_score": .8 if category in ["hiking", "wildlife", "photography"] else .3, "adventure_score": .85 if category in ["adventure", "water_sports", "hiking"] else .25, "culture_score": .85 if category in ["cultural", "historical", "food"] else .2, "beach_score": .9 if category in ["beach", "water_sports"] else .15, "wildlife_score": .9 if category == "wildlife" else .2, "wellness_score": .9 if category == "wellness" else .2, "shopping_score": .9 if category == "shopping" else .15, "family_score": .8 if category in ["sightseeing", "food", "photography"] else .45}
            writer.writerow([f"ACT{index + 1:03d}", f"{category.replace('_', ' ').title()} experience {index + 1}", f"DEST{destination_index + 1:03d}", destination[0], category, 1500 + (index % 12) * 700, round(1.5 + (index % 6) * .75, 1), round(3.8 + (index % 10) / 16, 1), emphasis["nature_score"], emphasis["adventure_score"], emphasis["culture_score"], emphasis["beach_score"], emphasis["wildlife_score"], emphasis["wellness_score"], emphasis["shopping_score"], emphasis["family_score"], category in ["food", "shopping", "wellness"], category not in ["food", "shopping", "wellness"], category not in ["adventure"], index % 8 != 0, destination[3] + .002, destination[4] + .002, f"Illustrative demo activity in {destination[0]}; verify details before real-world use."])

    with (DATA / "sample_user_interactions.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file); writer.writerow(["interaction_id", "user_id", "item_type", "item_id", "rating", "clicked", "saved", "booked", "timestamp"])
        for index in range(1, 31): writer.writerow([index, f"USER{index % 8 + 1:03d}", "destination", f"DEST{index % 12 + 1:03d}", 3 + index % 3, True, index % 2 == 0, index % 4 == 0, "2026-01-01"])

if __name__ == "__main__":
    write_catalogs(); print(f"Generated demo catalogs in {DATA}")

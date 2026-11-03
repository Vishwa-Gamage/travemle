from pathlib import Path
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "TRAVEMLE_Swagger_API_Test_Guide.docx"


def shade(cell, fill):
    properties = cell._tc.get_or_add_tcPr()
    element = OxmlElement("w:shd")
    element.set(qn("w:fill"), fill)
    properties.append(element)


def set_cell_text(cell, text, bold=False):
    cell.text = ""
    paragraph = cell.paragraphs[0]
    run = paragraph.add_run(str(text))
    run.bold = bold
    run.font.size = Pt(9)
    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER


def add_table(document, headers, rows):
    table = document.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    for index, header in enumerate(headers):
        set_cell_text(table.rows[0].cells[index], header, True)
        shade(table.rows[0].cells[index], "1F4E78")
        for run in table.rows[0].cells[index].paragraphs[0].runs:
            run.font.color.rgb = RGBColor(255, 255, 255)
    for row in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            set_cell_text(cells[index], value)
    document.add_paragraph()
    return table


def add_code(document, text):
    paragraph = document.add_paragraph()
    paragraph.style = "No Spacing"
    paragraph.paragraph_format.left_indent = Inches(.25)
    run = paragraph.add_run(text)
    run.font.name = "Consolas"
    run.font.size = Pt(9)
    return paragraph


def add_endpoint(document, method, path, purpose, body=None, expected=None, errors=None):
    heading = document.add_heading(level=2)
    run = heading.add_run(f"{method} {path}")
    run.font.color.rgb = RGBColor(31, 78, 121)
    document.add_paragraph(purpose)
    if body:
        document.add_paragraph("Request body:", style="Heading 3")
        add_code(document, body)
    if expected:
        document.add_paragraph("Expected response:", style="Heading 3")
        add_code(document, expected)
    if errors:
        document.add_paragraph("Validation and error checks:", style="Heading 3")
        for error in errors:
            document.add_paragraph(error, style="List Bullet")


doc = Document()
section = doc.sections[0]
section.top_margin = Inches(.65)
section.bottom_margin = Inches(.65)
section.left_margin = Inches(.75)
section.right_margin = Inches(.75)
styles = doc.styles
styles["Normal"].font.name = "Aptos"
styles["Normal"].font.size = Pt(10)
styles["Title"].font.name = "Aptos Display"
styles["Title"].font.color.rgb = RGBColor(31, 78, 121)

paragraph = doc.add_paragraph()
paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = paragraph.add_run("TRAVEMLE Smart Tour Planner")
run.bold = True
run.font.size = Pt(24)
run.font.color.rgb = RGBColor(31, 78, 121)
paragraph = doc.add_paragraph()
paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = paragraph.add_run("Swagger API Testing Guide")
run.bold = True
run.font.size = Pt(18)
paragraph = doc.add_paragraph()
paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
paragraph.add_run("Standalone FastAPI recommendation service | Version 1.0.0")
doc.add_paragraph()

doc.add_heading("1. Purpose", level=1)
doc.add_paragraph("This guide explains how to test every TRAVEMLE REST API endpoint through the interactive Swagger UI. The service is a content-based recommendation system using feature engineering, weighted ranking, and cosine similarity. The generated catalogs are demo data and do not represent verified live tourism information.")

doc.add_heading("2. Start the API", level=1)
doc.add_paragraph("Open PowerShell in the project folder and run:")
add_code(doc, "venv\\Scripts\\activate\n$env:CURL_CA_BUNDLE = \"\"\n$env:REQUESTS_CA_BUNDLE = \"\"\npython scripts\\generate_sample_data.py\npython run.py")
doc.add_paragraph("If the virtual environment does not contain the dependencies, install them with:")
add_code(doc, "venv\\Scripts\\python.exe -m pip install -r requirements.txt")
doc.add_paragraph("Open the Swagger interface in a browser:")
add_code(doc, "http://127.0.0.1:8000/docs")
doc.add_paragraph("For each endpoint, click the endpoint row, select Try it out, edit the JSON body where applicable, click Execute, and inspect the response code and response body.")

doc.add_heading("3. Test sequence", level=1)
add_table(doc, ["Order", "Endpoint", "Purpose"], [
    ["1", "GET /health", "Confirm that the API is running."],
    ["2", "POST /api/v1/profile", "Check user preference transformation."],
    ["3", "POST /api/v1/recommend/destinations", "Check destination ranking."],
    ["4", "GET /api/v1/destinations", "Inspect the destination catalog."],
    ["5", "GET /api/v1/destinations/{destination_id}", "Inspect one destination."],
    ["6", "POST /api/v1/recommend/accommodations", "Check accommodation filtering and ranking."],
    ["7", "GET /api/v1/accommodations", "Inspect accommodation records."],
    ["8", "POST /api/v1/recommend/activities", "Check activity ranking and category diversity."],
    ["9", "GET /api/v1/activities", "Inspect activity records."],
    ["10", "POST /api/v1/recommend/full-trip", "Check the composed trip recommendation."],
])

profile = '''{
  "budget": 100000,
  "trip_days": 4,
  "interests": ["nature", "adventure", "culture"],
  "preferred_activities": ["hiking", "sightseeing"],
  "travel_type": "couple",
  "accommodation_type": "hotel",
  "preferred_climate": "cool",
  "destination_type": "mountain",
  "min_hotel_rating": 4.0,
  "max_accommodation_price_per_night": 20000,
  "activity_budget": 25000,
  "preferred_activity_duration": "half_day",
  "family_friendly": false,
  "accessibility_required": false,
  "preferred_transport": "car",
  "top_n": 5
}'''

doc.add_heading("4. Core endpoint tests", level=1)
add_endpoint(doc, "GET", "/", "Confirm that the service identifies itself and exposes the documentation path.", expected='200 OK\n{"name":"TRAVEMLE ML API","status":"running","docs":"/docs"}')
add_endpoint(doc, "GET", "/health", "Basic health check for monitoring and deployment verification.", expected='200 OK\n{"status":"healthy"}')
add_endpoint(doc, "POST", "/api/v1/profile", "Convert preferences into a human-readable summary and numerical feature vector.", profile, '{\n  "human_readable": {"summary": "Couple traveller for 4 days", ...},\n  "feature_vector": {"nature_score": 1.0, "adventure_score": 1.0, ...}\n}', ["Expected status: 200.", "Confirm interests receive score 1.0 and numeric fields are normalized."])
add_endpoint(doc, "POST", "/api/v1/recommend/destinations", "Return ranked destinations using interest cosine similarity and business-rule compatibility.", profile, '{\n  "success": true,\n  "count": 5,\n  "recommendations": [{"destination_id":"DEST...", "recommendation_score":0.0, "match_percentage":0, "matched_interests":[], "reason":"..."}]\n}', ["Expected status: 200.", "Confirm count equals top_n.", "Confirm scores are between 0 and 1 and recommendations are ranked descending."])
add_endpoint(doc, "POST", "/api/v1/recommend/accommodations", "Filter stays by destination, price, rating, family/accessibility constraints, then rank facilities and compatibility.", '''{
  "destination_id": "DEST001",
  "max_price_per_night": 30000,
  "accommodation_type": "hotel",
  "min_rating": 4.0,
  "family_friendly": false,
  "accessibility_required": false,
  "preferred_facilities": ["wifi", "breakfast"],
  "top_n": 5
}''', '{\n  "success": true,\n  "count": 0,\n  "recommendations": [{"accommodation_id":"HOT...", "price_per_night":0, "rating":0.0, "matched_features":[]}]\n}', ["Expected status: 200.", "Every returned stay must be at or below the maximum price and at or above the minimum rating."])
add_endpoint(doc, "POST", "/api/v1/recommend/activities", "Rank activities at a destination using interests, preferred categories, remaining budget, available time, and constraints.", '''{
  "destination_id": "DEST001",
  "interests": ["nature", "adventure"],
  "preferred_activities": ["hiking", "sightseeing"],
  "remaining_budget": 25000,
  "available_hours": 8,
  "family_friendly": false,
  "accessibility_required": false,
  "top_n": 5
}''', '{\n  "success": true,\n  "count": 0,\n  "recommendations": [{"activity_id":"ACT...", "category":"hiking", "recommendation_score":0.0}]\n}', ["Expected status: 200.", "Confirm returned activities belong to the requested destination.", "Check that categories are varied where enough records are available."])
add_endpoint(doc, "POST", "/api/v1/recommend/full-trip", "Compose destination, accommodation, activity, and budget recommendations in one response.", profile, '{\n  "user_profile": {...},\n  "recommended_destination": {...},\n  "alternative_destinations": [...],\n  "recommended_accommodations": [...],\n  "recommended_activities": [...],\n  "budget_summary": {"total_budget":100000, "estimated_total":0, "remaining_budget":0}\n}', ["Expected status: 200.", "Confirm the selected destination has alternatives and that a budget summary is returned."])

doc.add_heading("5. Catalog endpoint tests", level=1)
add_endpoint(doc, "GET", "/api/v1/destinations", "Return all destination catalog records.", expected="200 OK\nExpected demo record count: 40")
add_endpoint(doc, "GET", "/api/v1/accommodations", "Return all accommodation catalog records.", expected="200 OK\nExpected demo record count: 120")
add_endpoint(doc, "GET", "/api/v1/activities", "Return all activity catalog records.", expected="200 OK\nExpected demo record count: 180")
add_endpoint(doc, "GET", "/api/v1/destinations/DEST001", "Return one destination by ID.", expected='200 OK\nRecord contains destination_id, destination_name, district, coordinates, scores, climate, and destination_type.')
add_endpoint(doc, "GET", "/api/v1/destinations/UNKNOWN", "Verify not-found handling.", expected='404 Not Found\n{"detail":"Destination not found"}')

doc.add_heading("6. Validation tests", level=1)
doc.add_paragraph("Use the following invalid request bodies in Swagger. FastAPI should return HTTP 422 Unprocessable Entity with validation details.")
add_table(doc, ["Test", "Change", "Expected result"], [
    ["Negative budget", '"budget": -1', "422; budget must be greater than zero."],
    ["Zero trip days", '"trip_days": 0', "422; trip_days must be greater than zero."],
    ["Missing budget", "Remove budget", "422; required field error."],
    ["Missing trip days", "Remove trip_days", "422; required field error."],
    ["Invalid top_n", '"top_n": 0 or 51', "422; top_n must be between 1 and 50."],
    ["Negative activity budget", '"remaining_budget": -100', "422; value must be greater than zero."],
    ["Negative accommodation price", '"max_price_per_night": -1', "422; value must be greater than zero."],
    ["Invalid rating range", '"min_hotel_rating": 6', "422; rating must be between 0 and 5."],
])

doc.add_heading("7. Profile scenarios", level=1)
doc.add_paragraph("Repeat the destination and full-trip tests with these profiles to demonstrate that ranking changes logically.")
add_table(doc, ["Scenario", "Budget", "Days", "Interests", "Optional preference"], [
    ["Beach traveller", "100000", "4", "beach, wellness", 'preferred_climate: tropical'],
    ["Cultural traveller", "80000", "3", "culture, shopping", 'destination_type: cultural'],
    ["Adventure traveller", "120000", "5", "adventure, nature", 'preferred_activities: hiking'],
    ["Family traveller", "150000", "5", "family, nature", 'family_friendly: true'],
    ["Budget traveller", "50000", "3", "nature, culture", 'accommodation_type: hostel'],
    ["Luxury traveller", "300000", "5", "luxury, wellness", 'min_hotel_rating: 4.5'],
])

doc.add_heading("8. What to record for a project demonstration", level=1)
for item in [
    "Screenshot the Swagger page showing GET /health returning 200.",
    "Screenshot one valid destination request and its ranked response.",
    "Record the recommendation count and top destination name.",
    "Screenshot one accommodation request showing price/rating filtering.",
    "Screenshot one activity request showing category and score fields.",
    "Screenshot the full-trip response showing budget_summary.",
    "Run the invalid budget test and record the 422 response.",
    "Run GET /api/v1/destinations/UNKNOWN and record the 404 response.",
    "Run python -m pytest -q and record the passing test count."
]:
    doc.add_paragraph(item, style="List Bullet")

doc.add_heading("9. Troubleshooting", level=1)
doc.add_paragraph("If ModuleNotFoundError: No module named uvicorn appears, install into the project environment explicitly:")
add_code(doc, "$env:CURL_CA_BUNDLE = \"\"\n$env:REQUESTS_CA_BUNDLE = \"\"\nvenv\\Scripts\\python.exe -m pip install -r requirements.txt")
doc.add_paragraph("If Swagger does not open, confirm that the terminal shows Uvicorn running on http://127.0.0.1:8000 and that no other process is using port 8000. Stop the server with Ctrl+C after testing.")

doc.add_heading("10. Automated verification", level=1)
add_code(doc, "venv\\Scripts\\activate\npython -m pytest -q")
doc.add_paragraph("The project test suite covers profile creation, invalid budget and duration validation, destination ranking, accommodation filtering, activity ranking, top_n behavior, API health, API validation, and full-trip recommendations.")

doc.add_paragraph()
footer = section.footer.paragraphs[0]
footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
footer.add_run("TRAVEMLE Swagger API Testing Guide | Demo data only").font.size = Pt(8)

doc.save(OUTPUT)
print(OUTPUT)

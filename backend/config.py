import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NVD_API_KEY = os.getenv("NVD_API_KEY", "")  # Optional: keyless CISA KEV + CCTV vulnerability catalog used automatically
DATABASE_PATH = os.getenv("DATABASE_PATH") or os.path.join(BASE_DIR, "data", "surveillancewatch.db")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# API Authentication
# ------------------
# DETECTION_API_KEY protects POST /api/detection-event against fabricated alert injection.
# An unauthenticated attacker being able to inject high-severity alerts is a real
# threat to a "trust score" system — documented deliberate design choice (Phase 4).
#
# Open/closed split (intentional, documented in report):
#   PROTECTED:  POST /api/detection-event  (requires X-API-Key header)
#   OPEN:       all GET routes — /api/devices, /api/alerts, /api/stats, etc.
#               The point of COBRA-WATCH is public surveillance transparency;
#               locking the read routes behind auth defeats that purpose.
#
# If DETECTION_API_KEY is empty (default for local dev), auth is DISABLED.
# Set it to a strong random value in production: openssl rand -hex 32
DETECTION_API_KEY = os.getenv("DETECTION_API_KEY", "")

CITIES = {
    "Mumbai":    {"lat": 19.0760, "lon": 72.8777, "zoom": 12},
    "Delhi":     {"lat": 28.6139, "lon": 77.2090, "zoom": 12},
    "Bangalore": {"lat": 12.9716, "lon": 77.5946, "zoom": 12},
    "Hyderabad": {"lat": 17.3850, "lon": 78.4867, "zoom": 12},
    "Chennai":   {"lat": 13.0827, "lon": 80.2707, "zoom": 12},
    "Kolkata":   {"lat": 22.5726, "lon": 88.3639, "zoom": 12},
    "Pune":      {"lat": 18.5204, "lon": 73.8567, "zoom": 12},
    "Ahmedabad": {"lat": 23.0225, "lon": 72.5714, "zoom": 12},
    "All India": {"lat": 20.5937, "lon": 78.9629, "zoom": 5},
}

SHODAN_QUERIES = [
    'city:"{city}" port:554',
    'city:"{city}" product:"Hikvision"',
    'city:"{city}" product:"Dahua"',
    'city:"{city}" http.title:"DVR"',
    'city:"{city}" product:"webcam"',
    'city:"{city}" product:"Network Camera"',
]

OWNER_TYPE_KEYWORDS = {
    "government": [
        "gov", "government", "municipal", "police", "ministry",
        "bsnl", "mtnl", "nic", "national informatics", "railways",
        "airport authority", "defence", "military", "state", "district",
        "corporation of", "smart city", "cantonment", "public works",
    ],
    "telecom": [
        "airtel", "jio", "vodafone", "idea", "vi ", "tata teleservices",
        "reliance", "bsnl", "mtnl", "telecom", "broadband", "isp",
        "bharti", "tata communications", "hathway", "you broadband",
        "act fibernet", "spectra", "excitel",
    ],
    "corporate": [
        "pvt", "private", "ltd", "limited", "inc", "corp", "solutions",
        "technologies", "systems", "services", "enterprises",
        "infosys", "wipro", "tcs", "tech mahindra", "hcl",
    ],
}

CACHE_TTL_HOURS = 24

WHOIS_BATCH_SIZE = 5
WHOIS_DELAY_SECONDS = 2.0

GROQ_MODEL = "llama-3.3-70b-versatile"

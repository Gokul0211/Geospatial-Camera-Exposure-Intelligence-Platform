import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SHODAN_API_KEY = os.getenv("SHODAN_API_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NVD_API_KEY = os.getenv("NVD_API_KEY", "")  # https://nvd.nist.gov/developers/request-an-api-key
DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "data", "surveillancewatch.db"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

CITIES = {
    "Mumbai":    {"lat": 19.0760, "lon": 72.8777, "zoom": 12},
    "Delhi":     {"lat": 28.6139, "lon": 77.2090, "zoom": 12},
    "Bangalore": {"lat": 12.9716, "lon": 77.5946, "zoom": 12},
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

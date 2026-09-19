import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
SEED_PATH = DATA_DIR / "seed.json"
DB_PATH = Path(os.environ.get("DISCUSSMEDS_DB", DATA_DIR / "indications.db"))

API_HOST = "127.0.0.1"
API_PORT = 18765

CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://127.0.0.1:41789,http://localhost:41789"
    ).split(",")
    if origin.strip()
]

# Compare tables stay readable at this cap (UI and API share the same limit).
COMPARE_LIMIT = 4
# Personal "currently taking" review can include a longer local list.
REVIEW_LIMIT = 50
EPIC_CLIENT_ID = os.environ.get("EPIC_CLIENT_ID", "").strip()
EPIC_REDIRECT_URI = os.environ.get(
    "EPIC_REDIRECT_URI",
    "http://127.0.0.1:18765/integrations/mychart/callback",
).strip()
EPIC_FHIR_BASE = os.environ.get(
    "EPIC_FHIR_BASE",
    "https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4",
).rstrip("/")
EPIC_AUTHORIZE_URL = os.environ.get(
    "EPIC_AUTHORIZE_URL",
    "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize",
)
EPIC_TOKEN_URL = os.environ.get(
    "EPIC_TOKEN_URL",
    "https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token",
)

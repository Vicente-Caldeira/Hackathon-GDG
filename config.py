"""
Configuration file for the document consistency checker.
"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
CACHE_DIR = PROJECT_ROOT / ".cache"

# Input files
INPUT_FILES = {
    "en": DATA_DIR / "test_sample_en_parsed.json",
    "de": DATA_DIR / "test_sample_de_parsed.json",
    "lv": DATA_DIR / "test_sample_lv_parsed.json"
}

# Ground truth
GROUND_TRUTH_FILE = DATA_DIR / "errors_test_file.xlsx"

# Watson AI configuration (MUST be set via environment variables)
# ⚠️ SECURITY: Never commit real API keys to version control!
# Set these before running with Watson AI:
#   export WATSON_API_KEY="your_key_here"
#   export WATSON_PROJECT_ID="your_project_id"
WATSON_API_KEY = os.getenv("WATSON_API_KEY", "")
WATSON_URL = os.getenv("WATSON_URL", "https://us-south.ml.cloud.ibm.com")
WATSON_PROJECT_ID = os.getenv("WATSON_PROJECT_ID", "")

# Embedding models
# BEST for multilingual (EN, DE, LV): IBM Granite Multilingual
WATSON_EMBEDDING_MODEL = "ibm/granite-embedding-107m-multilingual"

# Alternative Watson models
# - "ibm/slate-125m-english-rtrvr" (best for English-only, 768 dims)
# - "ibm/slate-30m-english-rtrvr" (faster, smaller, 384 dims)

# Fallback local model (if Watson not available)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Detection thresholds
# Note: Granite multilingual model averages 0.83 cross-lingual similarity in testing
# Setting threshold to 0.75 to avoid false "missing" matches
SIMILARITY_THRESHOLD = 0.75  # For paragraph alignment
NUMERICAL_TOLERANCE = 0.01   # For comparing decimal values

# Severity levels
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"

# Error types
ERROR_TYPES = {
    "MONETARY_VALUE": SEVERITY_CRITICAL,
    "CURRENCY_MISMATCH": SEVERITY_CRITICAL,
    "SCALE_ERROR": SEVERITY_CRITICAL,
    "LEGAL_REFERENCE": SEVERITY_CRITICAL,
    "ARTICLE_REFERENCE": SEVERITY_CRITICAL,
    "MISSING_VALUE": SEVERITY_CRITICAL,
    "DATE_VALUE": SEVERITY_MEDIUM,
    "NUMERIC_PRECISION": SEVERITY_MEDIUM,
    "CASE_NUMBER": SEVERITY_MEDIUM,
    "TYPO": SEVERITY_LOW
}

# Validation helper
def validate_watson_credentials() -> bool:
    """Check if Watson AI credentials are properly configured."""
    if not WATSON_API_KEY or WATSON_API_KEY.startswith("REPLACE_"):
        return False
    if not WATSON_PROJECT_ID or WATSON_PROJECT_ID.startswith("REPLACE_"):
        return False
    return True

def require_watson_credentials():
    """Raise error if Watson credentials are missing."""
    if not validate_watson_credentials():
        raise ValueError(
            "Watson AI credentials not configured!\n"
            "Set environment variables:\n"
            "  export WATSON_API_KEY='your_api_key'\n"
            "  export WATSON_PROJECT_ID='your_project_id'"
        )

# Create directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

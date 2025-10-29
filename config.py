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

# Watson AI configuration (set via environment variables)
WATSON_API_KEY = os.getenv("WATSON_API_KEY", "")
WATSON_URL = os.getenv("WATSON_URL", "https://us-south.ml.cloud.ibm.com")
WATSON_PROJECT_ID = os.getenv("WATSON_PROJECT_ID", "")

# Embedding model
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Fallback to local if Watson not available

# Detection thresholds
SIMILARITY_THRESHOLD = 0.85  # For paragraph alignment
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

# Create directories if they don't exist
OUTPUT_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

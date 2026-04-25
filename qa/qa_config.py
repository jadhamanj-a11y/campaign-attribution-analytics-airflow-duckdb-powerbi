from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "outputs"

DB_PATH = PROJECT_ROOT / "duckdb" / "campaign_analytics.duckdb"

# Raw source folders in this project
REQUIRED_RAW_FOLDERS = [
    "campaign_master",
    "grp_spots",
    "odec",
    "sessions",
]

# Auto-discover CSV files recursively from raw zone
REQUIRED_RAW_FILES = [
    str(p.relative_to(RAW_DIR)) for p in RAW_DIR.glob("**/*.csv")
]

MIN_ROW_COUNTS = {
    file_name: 1 for file_name in REQUIRED_RAW_FILES
}

# Schema checks will be added after we inspect actual columns
EXPECTED_SCHEMAS = {}

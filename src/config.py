from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
WAREHOUSE_DIR = ROOT / "warehouse"
REPORTS_DIR = ROOT / "reports"
DOCS_DIR = ROOT / "docs"
SQL_DIR = ROOT / "sql"
DB_PATH = WAREHOUSE_DIR / "control_tower.db"

START_DATE = "2026-01-01"
END_DATE = "2026-06-30"
RANDOM_SEED = 42

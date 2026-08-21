"""Remove only artifacts that this project can deterministically rebuild."""

from .build_warehouse import TABLE_SPECS
from .config import DB_PATH, DOCS_DIR, RAW_DIR, REPORTS_DIR


def main() -> None:
    explicit_paths = [RAW_DIR / spec["file"] for spec in TABLE_SPECS.values()]
    explicit_paths.extend(
        [
            RAW_DIR / "manifest.json",
            DB_PATH,
            DOCS_DIR / "data.js",
            REPORTS_DIR / "kpi_snapshot.csv",
            REPORTS_DIR / "action_queue.csv",
            REPORTS_DIR / "supplier_scorecard.csv",
            REPORTS_DIR / "executive_summary.md",
        ]
    )
    removed = 0
    for path in explicit_paths:
        if path.is_file():
            path.unlink()
            removed += 1
    print(f"Removed {removed} rebuildable project artifact(s).")


if __name__ == "__main__":
    main()

from __future__ import annotations

import hashlib
import json
import sqlite3
import unittest
from contextlib import closing

from src.build_warehouse import build
from src.config import DB_PATH, DOCS_DIR, RAW_DIR, REPORTS_DIR
from src.export_dashboard import export as export_dashboard
from src.export_report import export as export_report
from src.generate_data import generate


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        generate()
        build()
        export_dashboard()
        export_report()

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(DB_PATH)

    def test_generation_is_deterministic(self) -> None:
        paths = sorted(RAW_DIR.glob("*.csv")) + [RAW_DIR / "manifest.json"]
        before = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        generate()
        after = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        self.assertEqual(before, after)

    def test_manifest_matches_loaded_counts(self) -> None:
        manifest = json.loads((RAW_DIR / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["synthetic"])
        self.assertFalse(manifest["contains_personal_data"])
        with closing(self.connect()) as connection:
            db_count = sum(
                connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in (
                    "warehouses", "suppliers", "products", "customers", "orders",
                    "order_items", "procurement_receipts", "waste_events",
                )
            )
        self.assertEqual(sum(manifest["row_counts"].values()), db_count)

    def test_database_integrity_and_metric_contract(self) -> None:
        with closing(self.connect()) as connection:
            self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
            invalid_items = connection.execute(
                "SELECT COUNT(*) FROM order_items WHERE fulfilled_qty > ordered_qty OR fulfilled_qty < 0"
            ).fetchone()[0]
            self.assertEqual(invalid_items, 0)
            otif = connection.execute(
                "SELECT 100.0 * SUM(line_otif) / COUNT(*) FROM v_order_line_enriched"
            ).fetchone()[0]
            self.assertGreater(otif, 80)
            self.assertLess(otif, 95)

    def test_planted_incidents_are_detectable(self) -> None:
        query = """
            SELECT 100.0 * SUM(line_otif) / COUNT(*)
            FROM v_order_line_enriched
            WHERE city = ? AND category = ? AND order_date BETWEEN ? AND ?
        """
        cases = [
            ("Bengaluru", "Fresh Produce", "2026-04-15", "2026-05-12", "2026-03-18", "2026-04-14"),
            ("Mumbai", "Frozen Foods", "2026-02-10", "2026-03-05", "2026-01-17", "2026-02-09"),
            ("Pune", "Dairy", "2026-06-01", "2026-06-20", "2026-05-12", "2026-05-31"),
        ]
        with closing(self.connect()) as connection:
            for city, category, start, end, baseline_start, baseline_end in cases:
                incident = connection.execute(query, (city, category, start, end)).fetchone()[0]
                baseline = connection.execute(
                    query, (city, category, baseline_start, baseline_end)
                ).fetchone()[0]
                self.assertGreater(baseline - incident, 15, f"{city} × {category}")

    def test_portfolio_outputs_are_safe_and_present(self) -> None:
        index = (DOCS_DIR / "index.html").read_text(encoding="utf-8")
        data = (DOCS_DIR / "data.js").read_text(encoding="utf-8")
        self.assertNotIn("https://cdn", index)
        self.assertIn("Deterministic synthetic data", data)
        self.assertTrue((REPORTS_DIR / "executive_summary.md").is_file())
        self.assertTrue((REPORTS_DIR / "action_queue.csv").is_file())


if __name__ == "__main__":
    unittest.main()

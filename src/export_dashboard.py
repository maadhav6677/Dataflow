"""Export compact warehouse extracts for the dependency-free web dashboard."""

from __future__ import annotations

import json
import sqlite3

from .config import DB_PATH, DOCS_DIR, END_DATE, START_DATE


LINE_QUERY = """
SELECT
    order_date, city, category, order_id, customer_id, delivery_model,
    ordered_qty, fulfilled_qty,
    ROUND(ordered_value, 2), ROUND(delivered_value, 2), ROUND(gross_profit, 2),
    line_otif, is_late, is_cancelled, failure_reason
FROM v_order_line_enriched
ORDER BY order_date, order_id, line_number
"""

RECEIPT_QUERY = """
SELECT
    r.expected_date, w.city, p.category, s.supplier_name,
    r.ordered_qty, r.received_qty, r.rejected_qty,
    CASE WHEN r.received_date <= r.expected_date THEN 1 ELSE 0 END AS on_time,
    r.unit_cost
FROM procurement_receipts AS r
JOIN warehouses AS w ON w.warehouse_id = r.warehouse_id
JOIN products AS p ON p.product_id = r.product_id
JOIN suppliers AS s ON s.supplier_id = r.supplier_id
ORDER BY r.expected_date, r.receipt_id
"""

WASTE_QUERY = """
SELECT event_date, city, category, reason, waste_units, waste_cost
FROM mart_waste_daily
ORDER BY event_date, city, category, reason
"""


def _rows(connection: sqlite3.Connection, query: str) -> list[list]:
    return [list(row) for row in connection.execute(query).fetchall()]


def export() -> dict[str, int]:
    if not DB_PATH.is_file():
        raise FileNotFoundError("Warehouse missing. Run `make warehouse` first.")
    connection = sqlite3.connect(DB_PATH)
    try:
        payload = {
            "meta": {
                "title": "B2B Food Supply — Service & Waste Control Tower",
                "period_start": START_DATE,
                "period_end": END_DATE,
                "source": "Deterministic synthetic demonstration data; no real company records",
                "currency": "INR",
                "targets": {"line_otif": 95, "fill_rate": 98, "waste_rate": 1},
            },
            "schema": {
                "lines": [
                    "date", "city", "category", "order_id", "customer_id", "delivery_model",
                    "ordered_qty", "fulfilled_qty", "ordered_value", "delivered_value",
                    "gross_profit", "line_otif", "is_late", "is_cancelled", "failure_reason",
                ],
                "receipts": [
                    "date", "city", "category", "supplier", "ordered_qty", "received_qty",
                    "rejected_qty", "on_time", "unit_cost",
                ],
                "waste": ["date", "city", "category", "reason", "waste_units", "waste_cost"],
            },
            "lines": _rows(connection, LINE_QUERY),
            "receipts": _rows(connection, RECEIPT_QUERY),
            "waste": _rows(connection, WASTE_QUERY),
        }
    finally:
        connection.close()

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # Assign to a global instead of fetch() so the dashboard works from file:// too.
    output = "window.CONTROL_TOWER_DATA=" + encoded.replace("</", "<\\/") + ";\n"
    data_path = DOCS_DIR / "data.js"
    temp_path = data_path.with_suffix(".js.tmp")
    temp_path.write_text(output, encoding="utf-8")
    temp_path.replace(data_path)
    return {
        "order_lines": len(payload["lines"]),
        "receipts": len(payload["receipts"]),
        "waste_groups": len(payload["waste"]),
    }


def main() -> None:
    counts = export()
    print(
        "Exported dashboard data: "
        + ", ".join(f"{name}={count:,}" for name, count in counts.items())
        + "."
    )


if __name__ == "__main__":
    main()

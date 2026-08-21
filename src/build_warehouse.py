"""Validate raw CSV inputs and atomically build the SQLite analytics warehouse."""

from __future__ import annotations

import csv
import json
import sqlite3
from pathlib import Path
from typing import Callable

from .config import DB_PATH, RAW_DIR, SQL_DIR, WAREHOUSE_DIR


TABLE_SPECS: dict[str, dict] = {
    "warehouses": {
        "file": "warehouses.csv",
        "columns": ["warehouse_id", "city", "region"],
        "types": {},
    },
    "suppliers": {
        "file": "suppliers.csv",
        "columns": ["supplier_id", "supplier_name", "category", "base_delay_risk", "base_reject_risk"],
        "types": {"base_delay_risk": float, "base_reject_risk": float},
    },
    "products": {
        "file": "products.csv",
        "columns": [
            "product_id", "product_name", "category", "unit_cost", "list_price",
            "shelf_life_days", "cold_chain_required", "primary_supplier_id",
        ],
        "types": {
            "unit_cost": float, "list_price": float, "shelf_life_days": int,
            "cold_chain_required": int,
        },
    },
    "customers": {
        "file": "customers.csv",
        "columns": ["customer_id", "city", "business_type", "joined_date"],
        "types": {},
    },
    "orders": {
        "file": "orders.csv",
        "columns": [
            "order_id", "customer_id", "warehouse_id", "order_date", "promised_date",
            "delivered_date", "delivery_model", "order_status", "failure_reason",
        ],
        "types": {},
    },
    "order_items": {
        "file": "order_items.csv",
        "columns": [
            "order_id", "line_number", "product_id", "ordered_qty", "fulfilled_qty",
            "selling_price", "unit_cost",
        ],
        "types": {
            "line_number": int, "ordered_qty": int, "fulfilled_qty": int,
            "selling_price": float, "unit_cost": float,
        },
    },
    "procurement_receipts": {
        "file": "procurement_receipts.csv",
        "columns": [
            "receipt_id", "supplier_id", "warehouse_id", "product_id", "expected_date",
            "received_date", "ordered_qty", "received_qty", "rejected_qty", "unit_cost",
        ],
        "types": {
            "ordered_qty": int, "received_qty": int, "rejected_qty": int, "unit_cost": float,
        },
    },
    "waste_events": {
        "file": "waste_events.csv",
        "columns": [
            "event_id", "event_date", "warehouse_id", "product_id", "reason", "quantity", "unit_cost",
        ],
        "types": {"quantity": int, "unit_cost": float},
    },
}


class DataQualityError(ValueError):
    """Raised when an input fails a contract before it reaches the warehouse."""


def _read_rows(table: str, spec: dict) -> list[tuple]:
    path = RAW_DIR / spec["file"]
    if not path.is_file():
        raise DataQualityError(f"Missing required input: {path.relative_to(RAW_DIR.parent.parent)}")
    expected_columns = spec["columns"]
    converters: dict[str, Callable] = spec["types"]
    rows: list[tuple] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_columns:
            raise DataQualityError(
                f"{spec['file']} schema changed: expected {expected_columns}, got {reader.fieldnames}"
            )
        for line_number, raw in enumerate(reader, start=2):
            converted: list[object] = []
            for column in expected_columns:
                value = raw[column].strip()
                if value == "" and column != "delivered_date":
                    raise DataQualityError(f"{spec['file']}:{line_number} has blank {column}")
                if column == "delivered_date" and value == "":
                    converted.append(None)
                    continue
                try:
                    converted.append(converters.get(column, str)(value))
                except (TypeError, ValueError) as exc:
                    raise DataQualityError(
                        f"{spec['file']}:{line_number} has invalid {column}={value!r}"
                    ) from exc
            rows.append(tuple(converted))
    if not rows:
        raise DataQualityError(f"{spec['file']} is empty")
    return rows


def _validate_manifest(row_counts: dict[str, int]) -> None:
    manifest_path = RAW_DIR / "manifest.json"
    if not manifest_path.is_file():
        raise DataQualityError("Missing data/raw/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("synthetic") is not True or manifest.get("contains_personal_data") is not False:
        raise DataQualityError("Manifest must assert synthetic data with no personal information")
    if manifest.get("row_counts") != row_counts:
        raise DataQualityError("Manifest row counts do not match the CSV inputs")


def _validate_business_rules(connection: sqlite3.Connection) -> None:
    checks = {
        "customer city and fulfilment warehouse city disagree": """
            SELECT COUNT(*) FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            JOIN warehouses w ON w.warehouse_id = o.warehouse_id
            WHERE c.city <> w.city
        """,
        "a product is mapped to a supplier in another category": """
            SELECT COUNT(*) FROM products p
            JOIN suppliers s ON s.supplier_id = p.primary_supplier_id
            WHERE p.category <> s.category
        """,
        "successful order is incorrectly labelled with a failure": """
            SELECT COUNT(*) FROM orders o
            WHERE o.failure_reason = 'None'
              AND (
                o.order_status <> 'Delivered'
                OR o.delivered_date > o.promised_date
                OR EXISTS (
                    SELECT 1 FROM order_items i
                    WHERE i.order_id = o.order_id AND i.fulfilled_qty < i.ordered_qty
                )
              )
        """,
        "order predates customer join date": """
            SELECT COUNT(*) FROM orders o
            JOIN customers c ON c.customer_id = o.customer_id
            WHERE o.order_date < c.joined_date
        """,
    }
    for message, sql in checks.items():
        failures = connection.execute(sql).fetchone()[0]
        if failures:
            raise DataQualityError(f"{failures} row(s): {message}")
    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise DataQualityError(f"Foreign key validation failed: {foreign_key_errors[:3]}")


def build() -> dict[str, int]:
    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = DB_PATH.with_suffix(".db.tmp")
    if temp_path.exists():
        temp_path.unlink()

    loaded: dict[str, int] = {}
    connection = sqlite3.connect(temp_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript((SQL_DIR / "01_schema.sql").read_text(encoding="utf-8"))
        with connection:
            for table, spec in TABLE_SPECS.items():
                rows = _read_rows(table, spec)
                columns = spec["columns"]
                placeholders = ", ".join("?" for _ in columns)
                column_list = ", ".join(columns)
                connection.executemany(
                    f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})", rows
                )
                loaded[spec["file"]] = len(rows)
        _validate_manifest(loaded)
        _validate_business_rules(connection)
        connection.executescript((SQL_DIR / "02_marts.sql").read_text(encoding="utf-8"))
        connection.execute("ANALYZE")
        connection.commit()
    except Exception:
        connection.close()
        if temp_path.exists():
            temp_path.unlink()
        raise
    else:
        connection.close()
        temp_path.replace(DB_PATH)
    return loaded


def main() -> None:
    counts = build()
    print(f"Validated and loaded {sum(counts.values()):,} rows into {DB_PATH.name}.")


if __name__ == "__main__":
    main()

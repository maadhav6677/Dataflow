"""Generate a deterministic, synthetic B2B food-supply dataset.

No scraped, customer, employee, or confidential company data is used. The
patterns are intentionally planted so the project has realistic analytical
findings instead of random noise.
"""

from __future__ import annotations

import csv
import json
import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from .config import END_DATE, RANDOM_SEED, RAW_DIR, START_DATE


CITIES = (
    {"warehouse_id": "WH_DEL", "city": "Delhi NCR", "stock_risk": 0.030, "late_risk": 0.035},
    {"warehouse_id": "WH_BLR", "city": "Bengaluru", "stock_risk": 0.040, "late_risk": 0.050},
    {"warehouse_id": "WH_MUM", "city": "Mumbai", "stock_risk": 0.038, "late_risk": 0.055},
    {"warehouse_id": "WH_PUN", "city": "Pune", "stock_risk": 0.047, "late_risk": 0.060},
)

CATEGORY_CATALOG = {
    "Fresh Produce": (
        ("Tomatoes, 1 kg", 30, 42, 7, False),
        ("Onions, 1 kg", 24, 34, 21, False),
        ("Green Capsicum, 1 kg", 62, 82, 8, False),
        ("Fresh Coriander, 500 g", 32, 47, 4, True),
    ),
    "Dairy": (
        ("Toned Milk, 1 L", 48, 60, 5, True),
        ("Butter, 500 g", 225, 278, 90, True),
        ("Paneer, 1 kg", 285, 355, 8, True),
        ("Mozzarella, 1 kg", 390, 475, 45, True),
    ),
    "Chicken & Eggs": (
        ("Eggs, tray of 30", 145, 184, 18, False),
        ("Chicken Breast, 1 kg", 235, 292, 4, True),
        ("Chicken Curry Cut, 1 kg", 180, 228, 3, True),
        ("Liquid Egg Mix, 1 kg", 120, 158, 7, True),
    ),
    "Frozen Foods": (
        ("French Fries, 2.5 kg", 270, 345, 270, True),
        ("Veg Burger Patty, 1 kg", 210, 278, 180, True),
        ("Chicken Nuggets, 1 kg", 295, 375, 180, True),
        ("Frozen Green Peas, 1 kg", 105, 142, 240, True),
    ),
    "Staples": (
        ("Basmati Rice, 25 kg", 1_650, 1_890, 365, False),
        ("Refined Flour, 25 kg", 800, 940, 180, False),
        ("Sunflower Oil, 15 L", 1_560, 1_795, 270, False),
        ("Toor Dal, 5 kg", 620, 735, 240, False),
    ),
    "Sauces & Seasoning": (
        ("Tomato Ketchup, 5 kg", 340, 425, 180, False),
        ("Mayonnaise, 1 kg", 145, 188, 120, False),
        ("Chilli Flakes, 500 g", 165, 218, 270, False),
        ("Garam Masala, 500 g", 195, 255, 240, False),
    ),
    "Packaging": (
        ("750 ml Meal Box, pack of 50", 310, 390, 730, False),
        ("Paper Cup 250 ml, pack of 100", 205, 268, 730, False),
        ("Wooden Cutlery Kit, pack of 100", 280, 355, 730, False),
        ("Paper Carry Bag, pack of 50", 225, 290, 730, False),
    ),
    "Cleaning & Consumables": (
        ("Dishwash Liquid, 5 L", 295, 380, 540, False),
        ("Kitchen Degreaser, 5 L", 420, 525, 540, False),
        ("Food-safe Gloves, box of 100", 255, 335, 730, False),
        ("Kitchen Wipes, roll of 100", 115, 155, 730, False),
    ),
}

SUPPLIER_CATALOG = {
    "Fresh Produce": (("GreenBasket Farms", 0.04, 0.015), ("HarvestLink Produce", 0.08, 0.030)),
    "Dairy": (("MilkyWay Foods", 0.04, 0.012), ("Urban Dairy Co-op", 0.07, 0.025)),
    "Chicken & Eggs": (("FarmFresh Proteins", 0.05, 0.018), ("Prime Poultry", 0.08, 0.030)),
    "Frozen Foods": (("FrostBite Foods", 0.05, 0.015), ("NorthStar Frozen", 0.09, 0.025)),
    "Staples": (("GrainRoute Wholesale", 0.03, 0.008), ("PantrySource", 0.055, 0.015)),
    "Sauces & Seasoning": (("FlavourCraft", 0.035, 0.010), ("SpiceWorks", 0.060, 0.020)),
    "Packaging": (("PackRight Solutions", 0.04, 0.008), ("EcoServe Packaging", 0.07, 0.015)),
    "Cleaning & Consumables": (("CleanPro Supply", 0.03, 0.008), ("HygieneHub", 0.055, 0.012)),
}

CATEGORY_ORDER_WEIGHTS = {
    "Fresh Produce": 1.45,
    "Dairy": 1.25,
    "Chicken & Eggs": 1.10,
    "Frozen Foods": 0.95,
    "Staples": 0.85,
    "Sauces & Seasoning": 0.90,
    "Packaging": 1.00,
    "Cleaning & Consumables": 0.55,
}

BUSINESS_TYPES = ("Restaurant", "Cloud Kitchen", "Cafe & Bakery", "Caterer")


def _dates(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    """Write via a sibling temp file so interrupted runs do not corrupt inputs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields, extrasaction="raise", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(path)


def _incident(day: date, city: str, category: str) -> dict[str, float | str]:
    """Return planted operational stress; empty values are the normal baseline."""
    result: dict[str, float | str] = {
        "stock": 0.0,
        "late": 0.0,
        "reject": 0.0,
        "waste": 0.0,
        "reason": "",
    }
    if city == "Mumbai" and category == "Frozen Foods" and date(2026, 2, 10) <= day <= date(2026, 3, 5):
        result.update(stock=0.19, late=0.24, reject=0.025, waste=0.045, reason="Cold-chain exception")
    elif city == "Bengaluru" and category == "Fresh Produce" and date(2026, 4, 15) <= day <= date(2026, 5, 12):
        result.update(stock=0.23, late=0.11, reject=0.060, waste=0.060, reason="Supplier delay")
    elif city == "Pune" and category == "Dairy" and date(2026, 6, 1) <= day <= date(2026, 6, 20):
        result.update(stock=0.21, late=0.18, reject=0.055, waste=0.040, reason="Quality rejection")
    elif city == "Delhi NCR" and category == "Packaging" and date(2026, 3, 10) <= day <= date(2026, 3, 25):
        result.update(stock=0.14, late=0.08, reject=0.010, waste=0.002, reason="Capacity constraint")
    return result


def _build_dimensions(rng: random.Random) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    warehouses = [
        {"warehouse_id": item["warehouse_id"], "city": item["city"], "region": "West" if item["city"] in {"Mumbai", "Pune"} else "North" if item["city"] == "Delhi NCR" else "South"}
        for item in CITIES
    ]

    suppliers: list[dict] = []
    supplier_lookup: dict[tuple[str, int], str] = {}
    supplier_number = 1
    for category, entries in SUPPLIER_CATALOG.items():
        for position, (name, delay_risk, reject_risk) in enumerate(entries):
            supplier_id = f"SUP{supplier_number:03d}"
            suppliers.append(
                {
                    "supplier_id": supplier_id,
                    "supplier_name": name,
                    "category": category,
                    "base_delay_risk": f"{delay_risk:.3f}",
                    "base_reject_risk": f"{reject_risk:.3f}",
                }
            )
            supplier_lookup[(category, position)] = supplier_id
            supplier_number += 1

    products: list[dict] = []
    product_number = 1
    for category, entries in CATEGORY_CATALOG.items():
        for position, (name, cost, price, shelf_life, cold_chain) in enumerate(entries):
            products.append(
                {
                    "product_id": f"SKU{product_number:03d}",
                    "product_name": name,
                    "category": category,
                    "unit_cost": f"{cost:.2f}",
                    "list_price": f"{price:.2f}",
                    "shelf_life_days": shelf_life,
                    "cold_chain_required": int(cold_chain),
                    "primary_supplier_id": supplier_lookup[(category, position % 2)],
                }
            )
            product_number += 1

    customers: list[dict] = []
    customer_number = 1
    for city_config in CITIES:
        city = str(city_config["city"])
        for position in range(60):
            if position < 44:
                joined = date(2025, 7, 1) + timedelta(days=rng.randint(0, 175))
            else:
                joined = date(2026, 1, 1) + timedelta(days=rng.randint(0, 125))
            customers.append(
                {
                    "customer_id": f"CUS{customer_number:04d}",
                    "city": city,
                    "business_type": rng.choices(BUSINESS_TYPES, weights=(46, 25, 20, 9), k=1)[0],
                    "joined_date": joined.isoformat(),
                }
            )
            customer_number += 1
    return warehouses, suppliers, products, customers


def _generate_orders(
    rng: random.Random, products: list[dict], customers: list[dict]
) -> tuple[list[dict], list[dict]]:
    start = date.fromisoformat(START_DATE)
    end = date.fromisoformat(END_DATE)
    products_by_category = {
        category: [product for product in products if product["category"] == category]
        for category in CATEGORY_CATALOG
    }
    categories = list(CATEGORY_CATALOG)
    category_weights = [CATEGORY_ORDER_WEIGHTS[item] for item in categories]
    customers_by_city = {
        str(city["city"]): [customer for customer in customers if customer["city"] == city["city"]]
        for city in CITIES
    }

    orders: list[dict] = []
    order_items: list[dict] = []
    order_number = 1

    for day in _dates(start, end):
        month_growth = 1 + (day.month - start.month) * 0.035
        for city_config in CITIES:
            city = str(city_config["city"])
            daily_orders = round(rng.randint(5, 9) * month_growth + (1 if day.weekday() >= 5 else 0))
            active_customers = [
                customer
                for customer in customers_by_city[city]
                if date.fromisoformat(str(customer["joined_date"])) <= day
            ]
            for _ in range(daily_orders):
                order_id = f"ORD{order_number:06d}"
                order_number += 1
                customer = rng.choice(active_customers)
                model = rng.choices(("Next-day", "Express"), weights=(76, 24), k=1)[0]
                promised_date = day + timedelta(days=0 if model == "Express" else 1)
                line_count = rng.choices((1, 2, 3, 4), weights=(18, 37, 30, 15), k=1)[0]

                chosen_categories = rng.choices(categories, weights=category_weights, k=line_count)
                chosen_products: list[dict] = []
                used_ids: set[str] = set()
                for category in chosen_categories:
                    available = [p for p in products_by_category[category] if p["product_id"] not in used_ids]
                    if not available:
                        available = [p for p in products if p["product_id"] not in used_ids]
                    product = rng.choice(available)
                    chosen_products.append(product)
                    used_ids.add(str(product["product_id"]))

                incidents = [_incident(day, city, str(product["category"])) for product in chosen_products]
                max_late = max(float(item["late"]) for item in incidents)
                max_stock = max(float(item["stock"]) for item in incidents)
                cancelled = rng.random() < 0.006 + max_stock * 0.035
                late = not cancelled and rng.random() < float(city_config["late_risk"]) + max_late

                provisional_items: list[dict] = []
                has_shortage = False
                strongest_incident = max(incidents, key=lambda item: float(item["stock"]) + float(item["late"]))
                for line_number, product in enumerate(chosen_products, start=1):
                    category = str(product["category"])
                    incident = _incident(day, city, category)
                    ordered_qty = rng.randint(1, 7 if category not in {"Staples", "Packaging"} else 3)
                    stock_probability = float(city_config["stock_risk"]) + float(incident["stock"])
                    category_addition = 0.025 if category == "Fresh Produce" else 0.012 if category == "Dairy" else 0.0
                    if cancelled:
                        fulfilled_qty = 0
                    elif rng.random() < stock_probability + category_addition:
                        fulfilled_qty = max(0, math.floor(ordered_qty * rng.choice((0.0, 0.5, 0.75))))
                    else:
                        fulfilled_qty = ordered_qty
                    has_shortage = has_shortage or fulfilled_qty < ordered_qty
                    discount = rng.choice((0.00, 0.00, 0.02, 0.03, 0.05))
                    selling_price = round(float(product["list_price"]) * (1 - discount), 2)
                    unit_cost = round(float(product["unit_cost"]) * rng.uniform(0.985, 1.02), 2)
                    provisional_items.append(
                        {
                            "order_id": order_id,
                            "line_number": line_number,
                            "product_id": product["product_id"],
                            "ordered_qty": ordered_qty,
                            "fulfilled_qty": fulfilled_qty,
                            "selling_price": f"{selling_price:.2f}",
                            "unit_cost": f"{unit_cost:.2f}",
                        }
                    )

                if cancelled:
                    reason = "Customer cancellation" if rng.random() < 0.45 else "Stockout"
                    status = "Cancelled"
                    delivered_date = ""
                else:
                    status = "Delivered"
                    delivered_date = (promised_date + timedelta(days=rng.choice((1, 1, 2))) if late else promised_date).isoformat()
                    planted_reason = str(strongest_incident["reason"])
                    if (has_shortage or late) and planted_reason and rng.random() < 0.78:
                        reason = planted_reason
                    elif has_shortage:
                        reason = rng.choices(
                            ("Stockout", "Supplier delay", "Quality rejection"),
                            weights=(58, 27, 15),
                            k=1,
                        )[0]
                    elif late:
                        reason = rng.choices(
                            ("Capacity constraint", "Supplier delay", "Cold-chain exception"),
                            weights=(65, 25, 10),
                            k=1,
                        )[0]
                    else:
                        reason = "None"

                orders.append(
                    {
                        "order_id": order_id,
                        "customer_id": customer["customer_id"],
                        "warehouse_id": city_config["warehouse_id"],
                        "order_date": day.isoformat(),
                        "promised_date": promised_date.isoformat(),
                        "delivered_date": delivered_date,
                        "delivery_model": model,
                        "order_status": status,
                        "failure_reason": reason,
                    }
                )
                order_items.extend(provisional_items)

    return orders, order_items


def _generate_procurement(
    rng: random.Random, products: list[dict], suppliers: list[dict]
) -> tuple[list[dict], list[dict]]:
    start = date.fromisoformat(START_DATE)
    end = date.fromisoformat(END_DATE)
    supplier_by_id = {str(item["supplier_id"]): item for item in suppliers}
    receipts: list[dict] = []
    waste_events: list[dict] = []
    receipt_number = 1
    event_number = 1

    for day in _dates(start, end):
        for city_config in CITIES:
            city = str(city_config["city"])
            selected_products = rng.sample(products, k=rng.randint(3, 6))
            for product in selected_products:
                category = str(product["category"])
                supplier = supplier_by_id[str(product["primary_supplier_id"])]
                incident = _incident(day, city, category)
                ordered_qty = rng.randint(45, 180)
                delay_probability = float(supplier["base_delay_risk"]) + float(incident["late"]) * 0.65
                is_late = rng.random() < delay_probability
                received_date = day + timedelta(days=rng.choice((1, 1, 2)) if is_late else 0)
                short_qty = rng.randint(1, max(1, ordered_qty // 12)) if rng.random() < 0.035 + float(incident["stock"]) * 0.2 else 0
                received_qty = ordered_qty - short_qty
                reject_probability = float(supplier["base_reject_risk"]) + float(incident["reject"])
                rejected_qty = rng.randint(1, max(1, received_qty // 10)) if rng.random() < reject_probability else 0
                receipt_id = f"REC{receipt_number:06d}"
                receipt_number += 1
                unit_cost = round(float(product["unit_cost"]) * rng.uniform(0.98, 1.025), 2)
                receipts.append(
                    {
                        "receipt_id": receipt_id,
                        "supplier_id": supplier["supplier_id"],
                        "warehouse_id": city_config["warehouse_id"],
                        "product_id": product["product_id"],
                        "expected_date": day.isoformat(),
                        "received_date": received_date.isoformat(),
                        "ordered_qty": ordered_qty,
                        "received_qty": received_qty,
                        "rejected_qty": rejected_qty,
                        "unit_cost": f"{unit_cost:.2f}",
                    }
                )

                accepted_qty = received_qty - rejected_qty
                shelf_life = int(product["shelf_life_days"])
                base_waste_probability = 0.14 if shelf_life <= 8 else 0.055 if shelf_life <= 30 else 0.018
                if accepted_qty > 0 and rng.random() < base_waste_probability + float(incident["waste"]):
                    max_waste = max(1, math.ceil(accepted_qty * (0.08 + float(incident["waste"]))))
                    waste_qty = rng.randint(1, max_waste)
                    event_date = min(end, received_date + timedelta(days=rng.randint(1, min(7, shelf_life))))
                    waste_events.append(
                        {
                            "event_id": f"WST{event_number:06d}",
                            "event_date": event_date.isoformat(),
                            "warehouse_id": city_config["warehouse_id"],
                            "product_id": product["product_id"],
                            "reason": rng.choices(
                                ("Expiry", "Spoilage", "Handling damage"),
                                weights=(45, 38, 17),
                                k=1,
                            )[0],
                            "quantity": waste_qty,
                            "unit_cost": f"{unit_cost:.2f}",
                        }
                    )
                    event_number += 1

    return receipts, waste_events


def generate() -> dict[str, int]:
    rng = random.Random(RANDOM_SEED)
    warehouses, suppliers, products, customers = _build_dimensions(rng)
    orders, order_items = _generate_orders(rng, products, customers)
    receipts, waste_events = _generate_procurement(rng, products, suppliers)

    datasets = {
        "warehouses.csv": (warehouses, ["warehouse_id", "city", "region"]),
        "suppliers.csv": (
            suppliers,
            ["supplier_id", "supplier_name", "category", "base_delay_risk", "base_reject_risk"],
        ),
        "products.csv": (
            products,
            [
                "product_id",
                "product_name",
                "category",
                "unit_cost",
                "list_price",
                "shelf_life_days",
                "cold_chain_required",
                "primary_supplier_id",
            ],
        ),
        "customers.csv": (customers, ["customer_id", "city", "business_type", "joined_date"]),
        "orders.csv": (
            orders,
            [
                "order_id",
                "customer_id",
                "warehouse_id",
                "order_date",
                "promised_date",
                "delivered_date",
                "delivery_model",
                "order_status",
                "failure_reason",
            ],
        ),
        "order_items.csv": (
            order_items,
            ["order_id", "line_number", "product_id", "ordered_qty", "fulfilled_qty", "selling_price", "unit_cost"],
        ),
        "procurement_receipts.csv": (
            receipts,
            [
                "receipt_id",
                "supplier_id",
                "warehouse_id",
                "product_id",
                "expected_date",
                "received_date",
                "ordered_qty",
                "received_qty",
                "rejected_qty",
                "unit_cost",
            ],
        ),
        "waste_events.csv": (
            waste_events,
            ["event_id", "event_date", "warehouse_id", "product_id", "reason", "quantity", "unit_cost"],
        ),
    }

    for filename, (rows, fields) in datasets.items():
        _write_csv(RAW_DIR / filename, rows, fields)

    counts = {filename: len(rows) for filename, (rows, _) in datasets.items()}
    manifest = {
        "dataset": "synthetic_service_waste_control_tower",
        "version": 1,
        "seed": RANDOM_SEED,
        "period": {"start": START_DATE, "end": END_DATE},
        "synthetic": True,
        "contains_personal_data": False,
        "row_counts": counts,
    }
    manifest_path = RAW_DIR / "manifest.json"
    temp_path = manifest_path.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temp_path.replace(manifest_path)
    return counts


def main() -> None:
    counts = generate()
    total = sum(counts.values())
    print(f"Generated {total:,} deterministic synthetic rows across {len(counts)} CSV files.")


if __name__ == "__main__":
    main()

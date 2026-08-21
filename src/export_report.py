"""Create a concise decision memo and CSV handoffs from the SQL warehouse."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from .config import DB_PATH, REPORTS_DIR


def _currency(value: float) -> str:
    if abs(value) >= 10_000_000:
        return f"₹{value / 10_000_000:.2f} Cr"
    if abs(value) >= 100_000:
        return f"₹{value / 100_000:.2f} L"
    if abs(value) >= 1_000:
        return f"₹{value / 1_000:.1f} K"
    return f"₹{value:,.0f}"


def _write_csv(path: Path, header: list[str], rows: list[tuple]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    temp_path.replace(path)


def _recommend(reason: str, waste_rate: float) -> str:
    if waste_rate > 1:
        return "Review FEFO rotation and category-level demand forecast"
    return {
        "Cold-chain exception": "Audit cold-chain handoffs and temperature exceptions",
        "Supplier delay": "Tighten supplier SLA and validate a backup source",
        "Quality rejection": "Increase inbound QC and review supplier corrective action",
        "Stockout": "Revisit safety stock and reorder-point assumptions",
        "Capacity constraint": "Rebalance picking and dispatch capacity",
        "Customer cancellation": "Review promise accuracy and cancellation cohort",
    }.get(reason, "Monitor weekly")


def _period_comparison(
    connection: sqlite3.Connection,
    city: str,
    category: str,
    current_start: str,
    current_end: str,
    baseline_start: str,
    baseline_end: str,
) -> tuple[float, float, float, float]:
    query = """
        SELECT
            100.0 * SUM(line_otif) / COUNT(*),
            100.0 * SUM(fulfilled_qty) / SUM(ordered_qty)
        FROM v_order_line_enriched
        WHERE city = ? AND category = ? AND order_date BETWEEN ? AND ?
    """
    current = connection.execute(query, (city, category, current_start, current_end)).fetchone()
    baseline = connection.execute(query, (city, category, baseline_start, baseline_end)).fetchone()
    return current[0], current[1], baseline[0], baseline[1]


def export() -> None:
    if not DB_PATH.is_file():
        raise FileNotFoundError("Warehouse missing. Run `make warehouse` first.")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    try:
        overall = connection.execute(
            """
            SELECT
                COUNT(DISTINCT order_id), COUNT(DISTINCT customer_id), COUNT(*),
                SUM(delivered_value), 100.0 * SUM(line_otif) / COUNT(*),
                100.0 * SUM(fulfilled_qty) / SUM(ordered_qty),
                100.0 * SUM(gross_profit) / SUM(delivered_value),
                SUM(ordered_value - delivered_value), SUM(ordered_value)
            FROM v_order_line_enriched
            """
        ).fetchone()
        waste = connection.execute(
            """
            SELECT
                COALESCE(SUM(quantity), 0), COALESCE(SUM(quantity * unit_cost), 0),
                100.0 * SUM(quantity) /
                    (SELECT SUM(received_qty - rejected_qty) FROM procurement_receipts)
            FROM waste_events
            """
        ).fetchone()

        action_rows = connection.execute(
            """
            SELECT
                a.city, a.category, a.line_otif_pct, a.fill_rate_pct,
                a.revenue_at_risk, a.waste_rate_pct, a.waste_cost,
                COALESCE((
                    SELECT x.failure_reason
                    FROM v_order_line_enriched AS x
                    WHERE x.city = a.city AND x.category = a.category AND x.line_otif = 0
                    GROUP BY x.failure_reason
                    ORDER BY COUNT(*) DESC
                    LIMIT 1
                ), 'None') AS top_failure_reason,
                a.priority_score
            FROM mart_action_queue AS a
            ORDER BY a.priority_score DESC
            """
        ).fetchall()

        supplier_rows = connection.execute(
            """
            SELECT
                supplier_name, category, SUM(receipts),
                ROUND(100.0 * SUM(on_time_receipts) / SUM(receipts), 2),
                ROUND(100.0 * (SUM(received_units) - SUM(rejected_units)) / SUM(ordered_units), 2),
                ROUND(SUM(rejected_cost), 2)
            FROM mart_supplier_performance
            GROUP BY supplier_name, category
            ORDER BY 0.55 * (100.0 * SUM(on_time_receipts) / SUM(receipts))
                   + 0.45 * (100.0 * (SUM(received_units) - SUM(rejected_units)) / SUM(ordered_units))
            """
        ).fetchall()

        failure_rows = connection.execute(
            """
            SELECT failure_reason, COUNT(*), ROUND(SUM(ordered_value - delivered_value), 2)
            FROM v_order_line_enriched
            WHERE line_otif = 0
            GROUP BY failure_reason
            ORDER BY COUNT(*) DESC
            """
        ).fetchall()

        blr = _period_comparison(
            connection, "Bengaluru", "Fresh Produce",
            "2026-04-15", "2026-05-12", "2026-03-18", "2026-04-14",
        )
        mum = _period_comparison(
            connection, "Mumbai", "Frozen Foods",
            "2026-02-10", "2026-03-05", "2026-01-17", "2026-02-09",
        )
        pune = _period_comparison(
            connection, "Pune", "Dairy",
            "2026-06-01", "2026-06-20", "2026-05-12", "2026-05-31",
        )
    finally:
        connection.close()

    orders, customers, lines, revenue, otif, fill, margin, unfulfilled, ordered_value = overall
    kpi_rows = [
        ("orders", orders, "Distinct orders"),
        ("buyers", customers, "Distinct synthetic customers"),
        ("order_lines", lines, "Order-line analysis grain"),
        ("delivered_revenue_inr", f"{revenue:.2f}", "Fulfilled quantity × selling price"),
        ("line_otif_pct", f"{otif:.2f}", "On time and fulfilled in full / order lines"),
        ("unit_fill_rate_pct", f"{fill:.2f}", "Fulfilled units / ordered units"),
        ("gross_margin_pct", f"{margin:.2f}", "Gross profit / delivered revenue"),
        ("unfulfilled_value_inr", f"{unfulfilled:.2f}", "Ordered value − delivered value"),
        ("waste_rate_pct", f"{waste[2]:.2f}", "Waste units / accepted procurement units"),
        ("waste_cost_inr", f"{waste[1]:.2f}", "Disposed units × procurement unit cost"),
    ]
    _write_csv(REPORTS_DIR / "kpi_snapshot.csv", ["metric", "value", "definition"], kpi_rows)

    action_export = [
        (
            row[0], row[1], f"{row[2]:.2f}", f"{row[3]:.2f}", f"{row[4]:.2f}",
            f"{row[5]:.2f}", f"{row[6]:.2f}", row[7], _recommend(row[7], row[5]),
            f"{0.3 * row[4] + 0.2 * row[6]:.2f}",
        )
        for row in action_rows
    ]
    _write_csv(
        REPORTS_DIR / "action_queue.csv",
        [
            "city", "category", "line_otif_pct", "fill_rate_pct", "unfulfilled_value_inr",
            "waste_rate_pct", "waste_cost_inr", "top_failure_reason", "recommended_action",
            "illustrative_protected_value_inr",
        ],
        action_export,
    )
    _write_csv(
        REPORTS_DIR / "supplier_scorecard.csv",
        ["supplier", "category", "receipts", "on_time_pct", "acceptance_fill_pct", "rejected_cost_inr"],
        supplier_rows,
    )

    top_failure = failure_rows[0]
    top_value_gap = max(action_rows, key=lambda row: row[4])
    worst_service_gap = min(action_rows, key=lambda row: row[2])
    top_five_opportunity = sum(0.3 * row[4] + 0.2 * row[6] for row in action_rows[:5])
    report = f"""# Executive decision memo

> Analysis uses deterministic synthetic data. This is not Hyperpure internal data and the recommendations are diagnostic hypotheses, not causal claims.

## Decision in one sentence

Prioritise incident-specific supplier and fulfilment checks in Bengaluru Fresh Produce, Mumbai Frozen Foods, and Pune Dairy, while treating Pune Staples as the largest recurring unfulfilled-value opportunity.

## Six-month scorecard

| KPI | Result | Working benchmark | Readout |
|---|---:|---:|---|
| Delivered revenue | {_currency(revenue)} | — | {orders:,} orders from {customers:,} synthetic buyers |
| Line OTIF | {otif:.1f}% | 95.0% | {otif - 95:.1f} pp below target |
| Unit fill rate | {fill:.1f}% | 98.0% | {fill - 98:.1f} pp below target |
| Gross margin | {margin:.1f}% | Monitor | Positive, but service recovery should be margin-aware |
| Unfulfilled value | {_currency(unfulfilled)} | Minimise | {100 * unfulfilled / ordered_value:.1f}% of ordered value |
| Waste rate | {waste[2]:.2f}% | ≤1.0% | {_currency(waste[1])} at procurement cost |

## What needs attention

1. **Bengaluru × Fresh Produce is the largest service gap.** Full-period line OTIF is {worst_service_gap[2]:.1f}%. During 15 Apr–12 May it fell to {blr[0]:.1f}% from {blr[2]:.1f}% in the preceding 28 days; fill rate fell from {blr[3]:.1f}% to {blr[1]:.1f}%. This is a sharp incident pattern, not just a weak average.
2. **Mumbai × Frozen Foods shows a cold-chain-shaped incident.** Line OTIF fell from {mum[2]:.1f}% to {mum[0]:.1f}% during 10 Feb–5 Mar, while fill rate declined from {mum[3]:.1f}% to {mum[1]:.1f}%.
3. **Pune × Dairy needs an inbound-quality and supply review.** During 1–20 Jun, line OTIF was {pune[0]:.1f}% versus {pune[2]:.1f}% in the prior 20 days; fill rate moved from {pune[3]:.1f}% to {pune[1]:.1f}%.
4. **Pune × {top_value_gap[1]} has the largest unfulfilled-value pool.** It represents {_currency(top_value_gap[4])}, even though the lowest service percentage appears elsewhere. This distinction prevents ranking only by percentages.
5. **{top_failure[0]} is the most frequent recorded failure mode.** It affects {top_failure[1]:,} failed lines. The supplier watchlist should be used as a drill-down, not proof that a supplier caused every downstream failure.

## Recommended 30-day operating rhythm

| Priority | Action | Owner | Success measure |
|---|---|---|---|
| 1 | Review PO adherence and backup sourcing for Bengaluru produce | Category + procurement | Restore weekly line OTIF above 90% |
| 2 | Audit temperature exceptions and handoffs for Mumbai frozen items | Warehouse + quality | Cold-chain exceptions back to baseline |
| 3 | Tighten inbound QC and corrective-action tracking for Pune dairy | Quality + supplier manager | Acceptance fill improves without excess waste |
| 4 | Recalculate safety stock for Pune staples using demand and lead-time variability | Inventory planning | Lower unfulfilled value with stable waste |
| 5 | Review the control tower weekly by warehouse × category | Operations analytics | Gaps closed, actions owned, no metric regressions |

Recovering **30% of unfulfilled value plus 20% of waste cost** across the top five ranked gaps would protect an illustrative **{_currency(top_five_opportunity)}** over the observed period. This is a transparent scenario, not a forecast.

## Metric boundary

- **Line OTIF:** an order line is successful only when its order is delivered on/before promise date and the line is fulfilled in full.
- **Unfulfilled value:** ordered value minus delivered value. It is a demand-loss proxy, not booked revenue.
- **Waste rate:** disposed units divided by accepted procurement units.
- **Supplier acceptance fill:** received units less rejected units, divided by ordered procurement units.
"""
    report_path = REPORTS_DIR / "executive_summary.md"
    temp_path = report_path.with_suffix(".md.tmp")
    temp_path.write_text(report, encoding="utf-8")
    temp_path.replace(report_path)


def main() -> None:
    export()
    print("Exported executive memo, KPI snapshot, action queue, and supplier scorecard.")


if __name__ == "__main__":
    main()

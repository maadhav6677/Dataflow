-- 1) Executive KPI scorecard. Line OTIF requires each order line to be both
-- on time and completely fulfilled; this avoids hiding partial fulfilment.
SELECT
    ROUND(SUM(delivered_value), 0) AS delivered_revenue,
    ROUND(100.0 * SUM(line_otif) / COUNT(*), 2) AS line_otif_pct,
    ROUND(100.0 * SUM(fulfilled_qty) / SUM(ordered_qty), 2) AS fill_rate_pct,
    ROUND(SUM(ordered_value - delivered_value), 0) AS revenue_at_risk,
    ROUND(100.0 * SUM(gross_profit) / SUM(delivered_value), 2) AS gross_margin_pct
FROM v_order_line_enriched;

-- 2) Pareto of failure reasons: where should an operations lead investigate?
WITH failures AS (
    SELECT
        failure_reason,
        COUNT(*) AS affected_lines,
        SUM(ordered_value - delivered_value) AS revenue_at_risk
    FROM v_order_line_enriched
    WHERE line_otif = 0
    GROUP BY failure_reason
),
ranked AS (
    SELECT
        *,
        SUM(affected_lines) OVER (ORDER BY affected_lines DESC) AS cumulative_lines,
        SUM(affected_lines) OVER () AS total_lines
    FROM failures
)
SELECT
    failure_reason,
    affected_lines,
    ROUND(revenue_at_risk, 0) AS revenue_at_risk,
    ROUND(100.0 * cumulative_lines / total_lines, 1) AS cumulative_failure_pct
FROM ranked
ORDER BY affected_lines DESC;

-- 3) Weekly trend separates a one-off incident from a persistent service gap.
SELECT
    strftime('%Y-W%W', order_date) AS order_week,
    city,
    ROUND(100.0 * SUM(line_otif) / COUNT(*), 2) AS line_otif_pct,
    ROUND(SUM(ordered_value - delivered_value), 0) AS revenue_at_risk
FROM v_order_line_enriched
GROUP BY order_week, city
ORDER BY order_week, city;

-- 4) Supplier scorecard combines delivery reliability and quality acceptance.
SELECT
    supplier_name,
    category,
    SUM(receipts) AS receipts,
    ROUND(100.0 * SUM(on_time_receipts) / SUM(receipts), 2) AS on_time_pct,
    ROUND(100.0 * (SUM(received_units) - SUM(rejected_units)) / SUM(ordered_units), 2) AS acceptance_fill_pct,
    ROUND(SUM(rejected_cost), 0) AS rejected_cost
FROM mart_supplier_performance
GROUP BY supplier_name, category
HAVING SUM(receipts) >= 20
ORDER BY on_time_pct, acceptance_fill_pct;

-- 5) Prioritised action queue: service risk and cash loss in one ranked output.
SELECT
    city,
    category,
    line_otif_pct,
    fill_rate_pct,
    waste_rate_pct,
    ROUND(revenue_at_risk, 0) AS revenue_at_risk,
    ROUND(waste_cost, 0) AS waste_cost,
    ROUND(priority_score, 0) AS priority_score
FROM mart_action_queue
ORDER BY priority_score DESC
LIMIT 10;

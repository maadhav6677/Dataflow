DROP VIEW IF EXISTS mart_action_queue;
DROP VIEW IF EXISTS mart_waste_daily;
DROP VIEW IF EXISTS mart_supplier_performance;
DROP VIEW IF EXISTS mart_daily_operations;
DROP VIEW IF EXISTS v_order_line_enriched;

CREATE VIEW v_order_line_enriched AS
SELECT
    o.order_id,
    oi.line_number,
    o.order_date,
    o.promised_date,
    o.delivered_date,
    o.delivery_model,
    o.order_status,
    o.failure_reason,
    w.warehouse_id,
    w.city,
    w.region,
    c.customer_id,
    c.business_type,
    p.product_id,
    p.product_name,
    p.category,
    p.primary_supplier_id,
    oi.ordered_qty,
    oi.fulfilled_qty,
    oi.selling_price,
    oi.unit_cost,
    oi.ordered_qty * oi.selling_price AS ordered_value,
    oi.fulfilled_qty * oi.selling_price AS delivered_value,
    oi.fulfilled_qty * (oi.selling_price - oi.unit_cost) AS gross_profit,
    CASE
        WHEN o.order_status = 'Delivered'
         AND o.delivered_date <= o.promised_date
         AND oi.fulfilled_qty = oi.ordered_qty
        THEN 1 ELSE 0
    END AS line_otif,
    CASE
        WHEN o.order_status = 'Delivered' AND o.delivered_date > o.promised_date
        THEN 1 ELSE 0
    END AS is_late,
    CASE WHEN o.order_status = 'Cancelled' THEN 1 ELSE 0 END AS is_cancelled,
    CASE WHEN oi.fulfilled_qty < oi.ordered_qty THEN 1 ELSE 0 END AS has_shortage
FROM orders AS o
JOIN order_items AS oi ON oi.order_id = o.order_id
JOIN products AS p ON p.product_id = oi.product_id
JOIN warehouses AS w ON w.warehouse_id = o.warehouse_id
JOIN customers AS c ON c.customer_id = o.customer_id;

CREATE VIEW mart_daily_operations AS
SELECT
    order_date,
    warehouse_id,
    city,
    category,
    COUNT(*) AS order_lines,
    COUNT(DISTINCT order_id) AS orders,
    COUNT(DISTINCT customer_id) AS active_customers,
    SUM(ordered_qty) AS ordered_units,
    SUM(fulfilled_qty) AS fulfilled_units,
    ROUND(SUM(ordered_value), 2) AS ordered_value,
    ROUND(SUM(delivered_value), 2) AS delivered_revenue,
    ROUND(SUM(ordered_value - delivered_value), 2) AS revenue_at_risk,
    ROUND(SUM(gross_profit), 2) AS gross_profit,
    SUM(line_otif) AS otif_lines,
    SUM(is_late) AS late_lines,
    SUM(is_cancelled) AS cancelled_lines,
    SUM(has_shortage) AS shortage_lines
FROM v_order_line_enriched
GROUP BY order_date, warehouse_id, city, category;

CREATE VIEW mart_supplier_performance AS
SELECT
    r.supplier_id,
    s.supplier_name,
    r.warehouse_id,
    w.city,
    p.category,
    COUNT(*) AS receipts,
    SUM(r.ordered_qty) AS ordered_units,
    SUM(r.received_qty) AS received_units,
    SUM(r.rejected_qty) AS rejected_units,
    SUM(CASE WHEN r.received_date <= r.expected_date THEN 1 ELSE 0 END) AS on_time_receipts,
    ROUND(100.0 * SUM(CASE WHEN r.received_date <= r.expected_date THEN 1 ELSE 0 END) / COUNT(*), 2) AS on_time_pct,
    ROUND(100.0 * (SUM(r.received_qty) - SUM(r.rejected_qty)) / SUM(r.ordered_qty), 2) AS acceptance_fill_pct,
    ROUND(SUM(r.rejected_qty * r.unit_cost), 2) AS rejected_cost
FROM procurement_receipts AS r
JOIN suppliers AS s ON s.supplier_id = r.supplier_id
JOIN warehouses AS w ON w.warehouse_id = r.warehouse_id
JOIN products AS p ON p.product_id = r.product_id
GROUP BY r.supplier_id, s.supplier_name, r.warehouse_id, w.city, p.category;

CREATE VIEW mart_waste_daily AS
SELECT
    e.event_date,
    e.warehouse_id,
    w.city,
    p.category,
    e.reason,
    SUM(e.quantity) AS waste_units,
    ROUND(SUM(e.quantity * e.unit_cost), 2) AS waste_cost
FROM waste_events AS e
JOIN warehouses AS w ON w.warehouse_id = e.warehouse_id
JOIN products AS p ON p.product_id = e.product_id
GROUP BY e.event_date, e.warehouse_id, w.city, p.category, e.reason;

CREATE VIEW mart_action_queue AS
WITH operations AS (
    SELECT
        warehouse_id,
        city,
        category,
        SUM(order_lines) AS order_lines,
        SUM(otif_lines) AS otif_lines,
        SUM(ordered_units) AS ordered_units,
        SUM(fulfilled_units) AS fulfilled_units,
        SUM(delivered_revenue) AS delivered_revenue,
        SUM(revenue_at_risk) AS revenue_at_risk,
        SUM(gross_profit) AS gross_profit
    FROM mart_daily_operations
    GROUP BY warehouse_id, city, category
),
waste AS (
    SELECT
        warehouse_id,
        city,
        category,
        SUM(waste_units) AS waste_units,
        SUM(waste_cost) AS waste_cost
    FROM mart_waste_daily
    GROUP BY warehouse_id, city, category
),
receipts AS (
    SELECT
        r.warehouse_id,
        w.city,
        p.category,
        SUM(r.received_qty - r.rejected_qty) AS accepted_units
    FROM procurement_receipts AS r
    JOIN warehouses AS w ON w.warehouse_id = r.warehouse_id
    JOIN products AS p ON p.product_id = r.product_id
    GROUP BY r.warehouse_id, w.city, p.category
)
SELECT
    o.warehouse_id,
    o.city,
    o.category,
    o.order_lines,
    ROUND(100.0 * o.otif_lines / o.order_lines, 2) AS line_otif_pct,
    ROUND(100.0 * o.fulfilled_units / o.ordered_units, 2) AS fill_rate_pct,
    ROUND(o.delivered_revenue, 2) AS delivered_revenue,
    ROUND(o.revenue_at_risk, 2) AS revenue_at_risk,
    ROUND(100.0 * o.gross_profit / NULLIF(o.delivered_revenue, 0), 2) AS gross_margin_pct,
    COALESCE(w.waste_units, 0) AS waste_units,
    COALESCE(w.waste_cost, 0) AS waste_cost,
    ROUND(100.0 * COALESCE(w.waste_units, 0) / NULLIF(r.accepted_units, 0), 2) AS waste_rate_pct,
    ROUND(
        o.revenue_at_risk
        + COALESCE(w.waste_cost, 0)
        + (100.0 - (100.0 * o.otif_lines / o.order_lines)) * 250,
        2
    ) AS priority_score
FROM operations AS o
LEFT JOIN waste AS w
    ON w.warehouse_id = o.warehouse_id AND w.category = o.category
LEFT JOIN receipts AS r
    ON r.warehouse_id = o.warehouse_id AND r.category = o.category;

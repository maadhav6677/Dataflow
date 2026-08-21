# Data and metric dictionary

This document is the data contract for the Service & Waste Control Tower. It describes the generated source files, SQLite tables, analytical views, dashboard extracts, and metric rules.

All entities are synthetic. Identifiers are non-identifying surrogate keys, and no field contains personal or confidential company data.

## Dataset conventions

| Convention | Contract |
|---|---|
| Observation period | `2026-01-01` through `2026-06-30` |
| Generator seed | `42` |
| Currency | Indian rupees (INR) |
| Dates | ISO 8601 calendar dates stored as `YYYY-MM-DD` text |
| Percentages | Displayed on a 0–100 scale; source risk parameters use 0–1 probabilities |
| Quantities | Integer units in the SKU's packaged unit; cross-SKU totals are illustrative |
| Missing values | Only `orders.delivered_date` may be absent, and only for cancelled orders |
| Source manifest | `data/raw/manifest.json` records the seed, period, privacy assertions, and row counts |
| Database schema | `sql/01_schema.sql` is authoritative for SQLite types and constraints |
| Analytical logic | `sql/02_marts.sql` is authoritative for views and marts |

### Controlled domains

- **Cities:** Bengaluru, Delhi NCR, Mumbai, Pune
- **Regions:** North, South, West
- **Categories:** Chicken & Eggs, Cleaning & Consumables, Dairy, Fresh Produce, Frozen Foods, Packaging, Sauces & Seasoning, Staples
- **Business types:** Restaurant, Cloud Kitchen, Cafe & Bakery, Caterer
- **Delivery models:** Next-day, Express
- **Order statuses:** Delivered, Cancelled
- **Failure reasons:** None, Stockout, Supplier delay, Quality rejection, Capacity constraint, Cold-chain exception, Customer cancellation
- **Waste reasons:** Expiry, Spoilage, Handling damage

## Source tables

| Table | Grain | Demo rows | Purpose |
|---|---|---:|---|
| `warehouses` | One warehouse | 4 | Fulfilment location and region lookup |
| `suppliers` | One synthetic supplier | 16 | Category ownership and generation risk parameters |
| `products` | One SKU | 32 | Product, category, commercial, shelf-life, and cold-chain attributes |
| `customers` | One synthetic food business | 240 | Buyer segment, city, and activation date |
| `orders` | One customer order | 5,715 | Promise, delivery status, and order-level failure reason |
| `order_items` | One order line | 13,855 | Ordered and fulfilled units with realised price and cost |
| `procurement_receipts` | One inbound SKU receipt | 3,225 | Supplier delivery timing, completeness, and quality acceptance |
| `waste_events` | One SKU disposal event | 172 | Disposed units and procurement cost by reason |

Raw CSV files use the same names with a `.csv` suffix. The CSV header order is validated by `src/build_warehouse.py` before loading.

## Column dictionary

`PK` means primary key and `FK` means foreign key. Unless marked nullable, every field is required.

### `warehouses`

| Column | SQLite type | Key or constraint | Definition |
|---|---|---|---|
| `warehouse_id` | TEXT | PK; format `WH_*` | Stable warehouse identifier |
| `city` | TEXT | Unique; controlled domain | City served by the warehouse |
| `region` | TEXT | Controlled domain | Geographic reporting region |

### `suppliers`

| Column | SQLite type | Key or constraint | Definition |
|---|---|---|---|
| `supplier_id` | TEXT | PK; format `SUP###` | Stable supplier identifier |
| `supplier_name` | TEXT | Unique | Synthetic display name |
| `category` | TEXT | Controlled domain | Product category supplied |
| `base_delay_risk` | REAL | 0–1 | Generator probability used to simulate a late inbound receipt before incident stress |
| `base_reject_risk` | REAL | 0–1 | Generator probability used to simulate a quality rejection before incident stress |

The two risk fields are simulation inputs, not observed supplier KPIs and not exposed as recommendations.

### `products`

| Column | SQLite type | Key or constraint | Definition |
|---|---|---|---|
| `product_id` | TEXT | PK; format `SKU###` | Stable SKU identifier |
| `product_name` | TEXT | Unique | Synthetic product and pack description |
| `category` | TEXT | Controlled domain | Reporting category |
| `unit_cost` | REAL | Greater than 0; INR | Baseline procurement cost used by the generator |
| `list_price` | REAL | At least `unit_cost`; INR | Baseline selling price before generated discounts |
| `shelf_life_days` | INTEGER | Greater than 0 | Illustrative shelf life in calendar days |
| `cold_chain_required` | INTEGER | 0 or 1 | Boolean flag: `1` requires temperature-controlled handling |
| `primary_supplier_id` | TEXT | FK → `suppliers.supplier_id` | Primary synthetic supplier; validated to match the product category |

### `customers`

| Column | SQLite type | Key or constraint | Definition |
|---|---|---|---|
| `customer_id` | TEXT | PK; format `CUS####` | Non-identifying synthetic buyer identifier |
| `city` | TEXT | Controlled domain | Buyer city; validated against the fulfilment warehouse city on each order |
| `business_type` | TEXT | Controlled domain | Restaurant, Cloud Kitchen, Cafe & Bakery, or Caterer |
| `joined_date` | TEXT | ISO date | First date on which the buyer may place an order |

No names, addresses, contact details, or other personal fields are generated.

### `orders`

| Column | SQLite type | Key or constraint | Definition |
|---|---|---|---|
| `order_id` | TEXT | PK; format `ORD######` | Stable order identifier |
| `customer_id` | TEXT | FK → `customers.customer_id` | Buyer placing the order |
| `warehouse_id` | TEXT | FK → `warehouses.warehouse_id` | Warehouse responsible for fulfilment |
| `order_date` | TEXT | ISO date | Order creation date and service-metric attribution date |
| `promised_date` | TEXT | ISO date; on/after `order_date` | Customer delivery promise date |
| `delivered_date` | TEXT | Nullable ISO date | Actual delivery date; null only when the order is cancelled |
| `delivery_model` | TEXT | Next-day or Express | Promise model selected for the order |
| `order_status` | TEXT | Delivered or Cancelled | Final synthetic order state |
| `failure_reason` | TEXT | Controlled domain | Order-level diagnostic label; `None` only for orders delivered on time and in full |

`failure_reason` is inherited by every line on the order in the analytical view. It is a known modelling limitation: a production source should capture line- or event-level reasons.

### `order_items`

| Column | SQLite type | Key or constraint | Definition |
|---|---|---|---|
| `order_id` | TEXT | Composite PK; FK → `orders.order_id` | Parent order |
| `line_number` | INTEGER | Composite PK; greater than 0 | Line sequence within the order |
| `product_id` | TEXT | FK → `products.product_id` | Ordered SKU |
| `ordered_qty` | INTEGER | Greater than 0 | Units requested |
| `fulfilled_qty` | INTEGER | 0 through `ordered_qty` | Units delivered or otherwise fulfilled |
| `selling_price` | REAL | Greater than 0; INR per unit | Realised unit selling price after generated discount |
| `unit_cost` | REAL | Greater than 0; INR per unit | Realised procurement cost used for line gross profit |

### `procurement_receipts`

| Column | SQLite type | Key or constraint | Definition |
|---|---|---|---|
| `receipt_id` | TEXT | PK; format `REC######` | Stable inbound receipt identifier |
| `supplier_id` | TEXT | FK → `suppliers.supplier_id` | Supplier responsible for the receipt |
| `warehouse_id` | TEXT | FK → `warehouses.warehouse_id` | Destination warehouse |
| `product_id` | TEXT | FK → `products.product_id` | Received SKU |
| `expected_date` | TEXT | ISO date | Expected receipt date and inbound-metric attribution date |
| `received_date` | TEXT | ISO date | Actual receipt date |
| `ordered_qty` | INTEGER | Greater than 0 | Units requested from the supplier |
| `received_qty` | INTEGER | 0 through `ordered_qty` | Units physically received before rejection |
| `rejected_qty` | INTEGER | 0 through `received_qty` | Received units rejected by inbound quality control |
| `unit_cost` | REAL | Greater than 0; INR per unit | Realised procurement cost for rejected-cost calculations |

Accepted units equal `received_qty - rejected_qty`.

### `waste_events`

| Column | SQLite type | Key or constraint | Definition |
|---|---|---|---|
| `event_id` | TEXT | PK; format `WST######` | Stable disposal-event identifier |
| `event_date` | TEXT | ISO date | Disposal date and waste-metric attribution date |
| `warehouse_id` | TEXT | FK → `warehouses.warehouse_id` | Warehouse recording the disposal |
| `product_id` | TEXT | FK → `products.product_id` | Disposed SKU |
| `reason` | TEXT | Expiry, Spoilage, or Handling damage | Recorded waste reason |
| `quantity` | INTEGER | Greater than 0 | Units disposed |
| `unit_cost` | REAL | Greater than 0; INR per unit | Procurement cost used to value the event |

## Analytical views and marts

### `v_order_line_enriched`

**Grain:** one order line.

This view joins orders, lines, products, warehouses, and customers. It carries the source attributes required by the dashboard and adds the following derived fields:

| Column | Definition |
|---|---|
| `ordered_value` | `ordered_qty × selling_price` |
| `delivered_value` | `fulfilled_qty × selling_price` |
| `gross_profit` | `fulfilled_qty × (selling_price − unit_cost)` |
| `line_otif` | `1` only when the order is Delivered, `delivered_date <= promised_date`, and the line is fulfilled in full; otherwise `0` |
| `is_late` | `1` when a delivered order arrives after its promise date |
| `is_cancelled` | `1` when `order_status = 'Cancelled'` |
| `has_shortage` | `1` when `fulfilled_qty < ordered_qty` |

### `mart_daily_operations`

**Grain:** `order_date × warehouse × category`.

| Measure | Definition |
|---|---|
| `order_lines` | Number of order lines |
| `orders` | Distinct orders |
| `active_customers` | Distinct buyers |
| `ordered_units`, `fulfilled_units` | Summed line quantities |
| `ordered_value`, `delivered_revenue` | Summed INR values |
| `revenue_at_risk` | Sum of `ordered_value − delivered_value`; named this way in SQL for backward compatibility, presented as unfulfilled value in the product |
| `gross_profit` | Summed line gross profit |
| `otif_lines`, `late_lines`, `cancelled_lines`, `shortage_lines` | Counts of the corresponding binary line flags |

### `mart_supplier_performance`

**Grain:** `supplier × warehouse × category` over the complete dataset.

It aggregates receipt counts and units, on-time receipts, acceptance fill, and rejected cost. `on_time_pct` and `acceptance_fill_pct` are stored on a 0–100 scale.

### `mart_waste_daily`

**Grain:** `event_date × warehouse × category × waste reason`.

It sums disposed units and `quantity × unit_cost`.

### `mart_action_queue`

**Grain:** `warehouse × category` over the complete dataset.

The mart brings service, commercial, and waste measures together. Its heuristic score is:

```text
priority_score = unfulfilled_value
               + waste_cost
               + (100 − line_otif_pct) × 250
```

The score is a transparent ranking device, not a currency forecast or optimisation result. The `250` weight expresses the relative importance assigned to each OTIF percentage-point gap in this demonstration.

## Metric contracts

| Metric | Numerator | Denominator | Grain and date rule | Empty-denominator behavior |
|---|---|---|---|---|
| Line OTIF | Sum of `line_otif` | Order-line count | Order line; attributed to `order_date` | Not displayed when no lines match |
| Unit fill rate | Sum of `fulfilled_qty` | Sum of `ordered_qty` | Order line; attributed to `order_date` | Not displayed when no ordered units match |
| Delivered revenue | Sum of `fulfilled_qty × selling_price` | None | Order line; attributed to `order_date` | Zero |
| Unfulfilled value | Sum of `(ordered_qty − fulfilled_qty) × selling_price` | None | Order line; attributed to `order_date` | Zero |
| Gross margin | Sum of gross profit | Delivered revenue | Order line; attributed to `order_date` | Not displayed when delivered revenue is zero |
| Waste rate | Sum of disposed units | Sum of accepted inbound units | Numerator uses `event_date`; denominator uses receipt `expected_date`, within the same dashboard filters | Not displayed when accepted units are zero |
| Waste cost | Sum of `quantity × unit_cost` | None | Waste event; attributed to `event_date` | Zero |
| Supplier on-time | Receipts where `received_date <= expected_date` | Receipt count | Receipt; attributed to `expected_date` | Not displayed when no receipts match |
| Acceptance fill | Sum of `received_qty − rejected_qty` | Sum of receipt `ordered_qty` | Receipt; attributed to `expected_date` | Not displayed when ordered units are zero |
| Illustrative protected value | 30% of unfulfilled value + 20% of waste cost | None | Top five ranked gaps in the current dashboard scope | Zero when no gaps match |

### Important interpretation rules

- OTIF is deliberately strict: a timely partial line fails.
- Cancelled order lines fail OTIF and contribute unfulfilled value.
- Revenue and unfulfilled value are analytical demand measures, not accounting ledger entries.
- Waste uses accepted inbound units rather than received units so rejected stock is not treated as usable inventory.
- Supplier metrics identify where to investigate; they do not prove that a supplier caused a downstream service failure.
- Dashboard date filters are applied independently to order, receipt, and waste dates as defined above.
- Category and warehouse filters are applied consistently across lines, receipts, and waste events.

## Working benchmarks

| Metric | Illustrative benchmark | Product behavior |
|---|---:|---|
| Line OTIF | 95% | Below target is highlighted as a service gap |
| Unit fill rate | 98% | Below target is highlighted as an availability gap |
| Waste rate | At or below 1% | Above guardrail influences the recommended next move |

These are working thresholds for the synthetic demonstration, not claimed targets for any real company.

## Dashboard extract contract

`src/export_dashboard.py` writes `docs/data.js` as a static browser-readable payload. It contains:

| Array | Grain | Date field | Source |
|---|---|---|---|
| `lines` | One enriched order line | `order_date` exposed as `date` | `v_order_line_enriched` |
| `receipts` | One inbound receipt | `expected_date` exposed as `date` | Receipt, warehouse, product, and supplier joins |
| `waste` | One daily waste group | `event_date` exposed as `date` | `mart_waste_daily` |

The dashboard recalculates its KPIs in the browser from the filtered extract. It makes no API request and does not query SQLite at runtime.

## Change control

When a source field or metric changes, update all affected contracts together:

1. Generator fields in `src/generate_data.py`
2. Loader contract in `src/build_warehouse.py`
3. SQLite schema or marts in `sql/`
4. Dashboard or report exporter in `src/`
5. This dictionary
6. Tests and committed reproducible outputs

The complete change workflow is documented in [`../CONTRIBUTING.md`](../CONTRIBUTING.md).

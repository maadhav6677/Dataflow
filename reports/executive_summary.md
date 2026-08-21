# Executive decision memo

> Analysis uses deterministic synthetic demonstration data, represents no real company, and provides diagnostic hypotheses rather than causal claims.

## Report context

| Field | Value |
|---|---|
| Observation period | 2026-01-01 through 2026-06-30 |
| Dataset | `synthetic_service_waste_control_tower` |
| Generator seed | `42` |
| Service grain | One order line, attributed to order date |
| Inbound grain | One procurement receipt, attributed to expected date |
| Currency | INR |

## Decision in one sentence

Prioritise incident-specific supplier and fulfilment checks in Bengaluru Fresh Produce, Mumbai Frozen Foods, and Pune Dairy, while treating Pune Staples as the largest recurring unfulfilled-value opportunity.

## Six-month scorecard

| KPI | Result | Working benchmark | Readout |
|---|---:|---:|---|
| Delivered revenue | ₹1.38 Cr | — | 5,715 orders from 240 synthetic buyers |
| Line OTIF | 89.5% | 95.0% | -5.5 pp below target |
| Unit fill rate | 96.3% | 98.0% | -1.7 pp below target |
| Gross margin | 17.6% | Monitor | Positive, but service recovery should be margin-aware |
| Unfulfilled value | ₹4.76 L | Minimise | 3.3% of ordered value |
| Waste rate | 0.27% | ≤1.0% | ₹1.81 L at procurement cost |

## What needs attention

1. **Bengaluru × Fresh Produce is the largest service gap.** Full-period line OTIF is 83.8%. During 15 Apr–12 May it fell to 56.5% from 92.2% in the preceding 28 days; fill rate fell from 97.6% to 77.7%. This is a sharp incident pattern, not just a weak average.
2. **Mumbai × Frozen Foods shows a cold-chain-shaped incident.** Line OTIF fell from 94.9% to 62.0% during 10 Feb–5 Mar, while fill rate declined from 98.3% to 88.9%.
3. **Pune × Dairy needs an inbound-quality and supply review.** During 1–20 Jun, line OTIF was 65.3% versus 90.3% in the prior 20 days; fill rate moved from 99.2% to 89.1%.
4. **Pune × Staples has the largest unfulfilled-value pool.** It represents ₹44.8 K, even though the lowest service percentage appears elsewhere. This distinction prevents ranking only by percentages.
5. **Supplier delay is the most frequent recorded failure mode.** It affects 424 failed lines. The supplier watchlist should be used as a drill-down, not proof that a supplier caused every downstream failure.

## Recommended 30-day operating rhythm

| Priority | Action | Owner | Success measure |
|---|---|---|---|
| 1 | Review PO adherence and backup sourcing for Bengaluru produce | Category + procurement | Restore weekly line OTIF above 90% |
| 2 | Audit temperature exceptions and handoffs for Mumbai frozen items | Warehouse + quality | Cold-chain exceptions back to baseline |
| 3 | Tighten inbound QC and corrective-action tracking for Pune dairy | Quality + supplier manager | Acceptance fill improves without excess waste |
| 4 | Recalculate safety stock for Pune staples using demand and lead-time variability | Inventory planning | Lower unfulfilled value with stable waste |
| 5 | Review the control tower weekly by warehouse × category | Operations analytics | Gaps closed, actions owned, no metric regressions |

Recovering **30% of unfulfilled value plus 20% of waste cost** across the top five ranked gaps would protect an illustrative **₹56.8 K** over the observed period. This is a transparent scenario, not a forecast.

## Metric boundary

- **Line OTIF:** an order line is successful only when its order is delivered on/before promise date and the line is fulfilled in full.
- **Unfulfilled value:** ordered value minus delivered value. It is a demand-loss proxy, not booked revenue.
- **Waste rate:** disposed units divided by accepted procurement units.
- **Supplier acceptance fill:** received units less rejected units, divided by ordered procurement units.

## Supporting artifacts

- [Interactive dashboard](../docs/index.html)
- [KPI snapshot](kpi_snapshot.csv)
- [Prioritised action queue](action_queue.csv)
- [Supplier scorecard](supplier_scorecard.csv)
- [Data and metric dictionary](../docs/data_dictionary.md)
- [Architecture and limitations](../docs/architecture.md)

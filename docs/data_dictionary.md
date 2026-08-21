# Data and metric dictionary

All entities are synthetic. IDs are non-identifying surrogate keys.

## Source tables

| Table | Grain | Purpose |
|---|---|---|
| `warehouses` | One warehouse | City and region lookup |
| `customers` | One synthetic food business | Buyer type and join date; no names or contact details |
| `suppliers` | One synthetic supplier | Category and data-generation risk parameters |
| `products` | One SKU | Category, price, cost, shelf life, cold-chain flag |
| `orders` | One order | Promise, delivery status, delivery model, failure reason |
| `order_items` | One order line | Ordered and fulfilled units, selling price, cost |
| `procurement_receipts` | One inbound receipt | Supplier timing, quantity, and quality acceptance |
| `waste_events` | One disposal event | Quantity and cost by expiry, spoilage, or damage |

## Metric contracts

| Metric | Formula | Why it matters |
|---|---|---|
| Line OTIF | Lines on time **and** in full / all lines | Prevents a timely partial order from looking successful |
| Unit fill rate | Fulfilled units / ordered units | Measures item availability independent of delivery timing |
| Delivered revenue | Fulfilled quantity × selling price | Value actually fulfilled in this analytical model |
| Unfulfilled value | Ordered value − delivered value | Demand-loss proxy; it is not recognised revenue |
| Gross margin | (Delivered value − fulfilled cost) / delivered value | Keeps service actions connected to economics |
| Waste rate | Disposed units / accepted procurement units | Normalises inventory loss for purchasing volume |
| Supplier on-time | Receipts arriving by expected date / receipts | Measures inbound delivery reliability |
| Acceptance fill | (Received − rejected units) / ordered units | Combines supplier completeness and inbound quality |

## Working benchmarks

The dashboard uses illustrative operating thresholds—not claimed Hyperpure targets:

- Line OTIF: 95%
- Unit fill rate: 98%
- Waste rate: at or below 1%

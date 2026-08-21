# Interview guide

## The 90-second explanation

“I wanted to analyse a problem close to Hyperpure’s core business: restaurants need reliable ingredients, but improving availability can create excess inventory and waste. I generated six months of synthetic orders, inbound receipts, and waste events across four warehouses. I validated the data in Python, modelled it in SQLite with reusable SQL marts, and built an interactive dashboard around line OTIF, fill rate, unfulfilled value, supplier reliability, and waste.

The headline is that network OTIF is 89.5%, but the average hides short, severe incidents. Bengaluru fresh produce fell from 92.2% to 56.5% OTIF during one period; Mumbai frozen and Pune dairy show similar event patterns. I ranked warehouse-category actions by both service gap and cash impact, then proposed supplier, cold-chain, inbound-quality, and safety-stock checks. I would validate those hypotheses with operational owners before calling them root causes.”

## Questions you should be ready for

### Why line OTIF instead of only fill rate?

Fill rate catches shortages but ignores timing. OTIF requires both a complete line and an on-time order, so a full but late delivery still fails the customer promise.

### Why SQLite instead of a cloud warehouse?

The dataset is deliberately small and portable. SQLite lets a reviewer reproduce the full SQL workflow with zero credentials or cost. The same fact/dimension logic and marts can be moved to BigQuery, Snowflake, or Redshift.

### Why synthetic data?

Real Hyperpure operational data is private. Synthetic data makes the portfolio safe and shareable. The important work here is metric design, validation, analytical diagnosis, and clear decisions—not pretending the data is real.

### Is the action queue a model?

No. It is a transparent prioritisation rule: unfulfilled value + waste cost + a service-gap weight. Recommendations follow the dominant recorded failure mode. It helps focus investigation but does not prove causality.

### What would you do next with real data?

Add promised delivery slots, inventory snapshots, purchase-order lead-time history, temperature-exception logs, substitutions, and restaurant reorder behaviour. Then validate whether proposed interventions improve service without reducing margin or increasing waste.

## Three honest limitations

1. The data-generating process plants incidents, so it is suitable for demonstrating diagnosis—not estimating real company performance.
2. Order-level failure reasons are assigned to each line; real systems should capture line-level reason codes where possible.
3. The protected-value scenario is arithmetic, not a forecast or causal effect estimate.

## Resume bullet

Built a reproducible B2B food-supply analytics control tower using Python, SQL, SQLite, and JavaScript; modelled 23K+ synthetic order/procurement records, defined OTIF/fill/waste KPIs, detected warehouse-category incidents, and ranked service recovery opportunities by operational and financial impact.

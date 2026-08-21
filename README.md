# B2B Food Supply — Service & Waste Control Tower

An end-to-end operations analytics project that answers one practical question:

> **Where are fulfilment failures and inventory losses concentrated, and what should an operations team fix first?**

[Open the interactive dashboard](docs/index.html) · [Read the decision memo](reports/executive_summary.md) · [Review the metric dictionary](docs/data_dictionary.md)

> **Data boundary:** every business record in this repository is deterministic synthetic data. This project is not affiliated with Hyperpure or Eternal and uses no internal, personal, or scraped operational data.

## Why this problem fits Hyperpure

Hyperpure describes itself as Eternal's B2B food-supply platform, with temperature-controlled logistics, 100,000+ outlets served in FY25, and 11 warehouses across India. Its public site emphasises predictable supply, fewer stockouts, reduced wastage, and reliable deliveries. Eternal's FY26 annual report says core restaurant supplies grew 38% year on year while the business moved into quarterly Adjusted EBITDA profitability. Together, those signals make **service reliability with cost discipline** a credible analytics problem—not a generic sales dashboard.

Sources: [Hyperpure business overview](https://www.eternal.com/our-businesses/hyperpure/), [Hyperpure public website](https://www.hyperpure.com/), and [Eternal FY26 Annual Report](https://b.zmtcdn.com/investor-relations/Eternal_Annual_Report_2025-26.pdf).

## Executive readout

The six-month synthetic network contains **5,715 orders, 13,855 order lines, 3,225 inbound receipts, and 240 buyers** across Delhi NCR, Bengaluru, Mumbai, and Pune.

| KPI | Result | Interpretation |
|---|---:|---|
| Delivered revenue | ₹1.38 Cr | Fulfilled value in the analytical model |
| Line OTIF | 89.5% | 5.5 percentage points below the illustrative 95% target |
| Unit fill rate | 96.3% | Availability is better than OTIF, so timing also matters |
| Unfulfilled value | ₹4.76 L | 3.3% of ordered value |
| Gross margin | 17.6% | Service recovery must remain margin-aware |
| Waste rate | 0.27% | ₹1.81 L at procurement cost |

The network average hides three sharp incidents:

- **Bengaluru × Fresh Produce:** line OTIF fell from 92.2% to 56.5% during a four-week supplier-delay pattern.
- **Mumbai × Frozen Foods:** line OTIF fell from 94.9% to 62.0% during a cold-chain-shaped incident.
- **Pune × Dairy:** line OTIF fell from 90.3% to 65.3% during an inbound-quality pattern.

Pune Staples, meanwhile, has the largest recurring unfulfilled-value pool at ₹44.8 K. That distinction is deliberate: the lowest percentage and the largest financial opportunity are not always the same.

## Dashboard

### Network overview

![Network overview showing the dashboard header, filters, and executive KPI scorecard](docs/assets/dashboard-overview.jpg)

### Warehouse-category incident drill-down

![Bengaluru Fresh Produce drill-down showing the filtered executive KPI scorecard](docs/assets/dashboard-incident.jpg)

The dashboard is fully offline and every KPI, visual, recommendation, and supplier score responds to the selected date, warehouse, and category filters.

## Technical scope

- **SQL:** fact/dimension joins, reusable views, CTEs, window functions, KPI contracts, Pareto analysis, and a ranked action mart.
- **Python:** deterministic data generation, CSV contracts, business-rule validation, atomic builds, and report exports.
- **Analytics:** separates service, availability, margin, supplier quality, and waste; compares incident windows with baselines; avoids claiming correlation as causation.
- **Reporting:** interactive dashboard, one-page decision memo, action queue, and supplier watchlist.
- **Engineering hygiene:** no runtime dependencies, no secrets, no external dashboard scripts, read-only CI permissions, tests, and explicit synthetic-data labelling.

## Technology stack

| Layer | Technology | Role in the project |
|---|---|---|
| Data generation and validation | Python 3.11+ standard library | Generates deterministic CSV data, enforces data contracts, validates business rules, and exports reports |
| Analytical database | SQLite | Stores the relational model, applies constraints and indexes, and provides a portable local warehouse |
| Transformation and analysis | SQL | Builds reusable analytical views and marts using joins, CTEs, aggregations, and window functions |
| Dashboard | HTML5, CSS3, Vanilla JavaScript, SVG | Provides offline filters, KPI scorecards, charts, diagnostics, and action tables without external libraries |
| Testing | Python `unittest` | Checks reproducibility, referential integrity, metric contracts, incident detection, and output safety |
| Workflow automation | GNU Make | Runs data generation, warehouse builds, dashboard exports, reports, tests, and cleanup |
| Continuous integration | GitHub Actions | Rebuilds and tests the project and verifies that committed analytical outputs are reproducible |
| Version control | Git | Tracks source code, SQL, documentation, generated reports, and dashboard assets |

## Workflow

```text
Synthetic CSV sources
        │
        ▼
Python contracts + quality checks
        │  schema, ranges, dates, relationships, business rules
        ▼
SQLite analytics warehouse
        │
        ├── SQL marts ──► executive memo + CSV action handoffs
        │
        └── compact extract ──► offline interactive dashboard
```

This is intentionally a small batch pipeline. A cloud warehouse, orchestration platform, or machine-learning layer would add complexity without improving the business answer at this scale.

## Run it locally

Requirements: Python 3.11+ and Make. There are no packages to install.

```bash
make setup
make test
python3 -m http.server 8000 --directory docs
```

Then open [http://localhost:8000](http://localhost:8000). The dashboard also works by opening `docs/index.html` directly.

Useful commands:

| Command | Purpose |
|---|---|
| `make setup` | Generate data, build the warehouse, dashboard extract, and report |
| `make test` | Run integrity, reproducibility, incident, and output-safety tests |
| `make check` | Rebuild everything and run the complete test suite |
| `make clean` | Remove only explicitly listed, reproducible artifacts |

## Repository map

```text
.
├── data/raw/                  # Generated CSV inputs (git-ignored)
├── docs/                      # Offline dashboard and metric dictionary
├── reports/                   # Decision memo and CSV handoffs
├── sql/                       # Schema, marts, and analyst-facing SQL queries
├── src/                       # Generation, validation, warehouse, and export code
├── tests/                     # Standard-library integration tests
├── warehouse/                 # Rebuildable SQLite database (git-ignored)
├── Makefile                   # One-command workflow
└── SECURITY.md                # Data and security boundary
```

Start with these files:

1. [`reports/executive_summary.md`](reports/executive_summary.md) — the business conclusion.
2. [`docs/index.html`](docs/index.html) — the interactive decision view.
3. [`sql/03_analysis.sql`](sql/03_analysis.sql) — the core analytical SQL.
4. [`src/build_warehouse.py`](src/build_warehouse.py) — validation and safe warehouse build.
5. [`docs/data_dictionary.md`](docs/data_dictionary.md) — grain and metric definitions.

## Metric choices

- **Line OTIF** succeeds only when an order is delivered on/before its promise date **and** that line is fulfilled in full.
- **Unfulfilled value** is ordered value minus delivered value. It is a demand-loss proxy, not booked revenue.
- **Waste rate** is disposed units divided by accepted inbound units.
- **Acceptance fill** is received units minus rejected units, divided by ordered procurement units.

The 95% OTIF, 98% fill-rate, and 1% waste thresholds are illustrative working benchmarks. They are not claimed Hyperpure targets. Full definitions are in the [data dictionary](docs/data_dictionary.md).

## Scope and limitations

- Planted incidents make the dataset useful for demonstrating diagnosis; they do not estimate real company performance.
- Order-level failure reasons are inherited by lines. A production system should capture line-level reason codes where possible.
- The protected-value scenario is transparent arithmetic, not a forecast.
- Recommended actions require validation with procurement, warehouse, quality, and category owners before execution.

Licensed under the [MIT License](LICENSE).

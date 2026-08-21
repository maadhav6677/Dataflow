# Contributing

Thank you for improving the Service & Waste Control Tower. This project values reproducible analytics, explicit metric contracts, small dependency surfaces, and documentation that stays aligned with the generated product.

## Development prerequisites

- Python 3.11 or newer
- GNU Make
- Git
- A modern browser for dashboard verification

The project has no third-party Python runtime dependencies.

## Set up and verify the project

From the repository root:

```bash
make check
python3 -m http.server 8000 --directory docs
```

Open [http://localhost:8000](http://localhost:8000) and verify the dashboard before changing it.

## Development workflow

1. Create a focused branch or working change.
2. Read the relevant contract in [`docs/data_dictionary.md`](docs/data_dictionary.md) and architecture notes in [`docs/architecture.md`](docs/architecture.md).
3. Make the smallest coherent source change.
4. Regenerate affected outputs rather than editing generated files by hand.
5. Run `make check`.
6. Inspect `git diff` for intentional source and generated-output changes.
7. Verify the dashboard in a browser when UI, metrics, extracts, or screenshots change.

Do not commit unrelated local state, generated SQLite databases, Python caches, editor configuration, or raw CSV files.

## Source and generated files

| Path | Source or generated | Version-controlled | Change rule |
|---|---|---|---|
| `src/`, `sql/`, `docs/index.html`, `docs/assets/app.js`, `docs/assets/styles.css` | Source | Yes | Edit directly |
| `data/raw/manifest.json` | Generated contract | Yes | Regenerate with `make data` |
| `data/raw/*.csv` | Generated data | No | Regenerate with `make data` |
| `warehouse/*.db` | Generated warehouse | No | Regenerate with `make warehouse` |
| `docs/data.js` | Generated dashboard extract | Yes | Regenerate with `make dashboard` |
| `reports/*` | Generated decision outputs | Yes | Regenerate with `make report` |
| `docs/assets/dashboard-*.jpg` | Captured product evidence | Yes | Recapture from a rebuilt dashboard |

Generated artifacts are committed where they let a reviewer open the dashboard and inspect conclusions without running a build. CI verifies that these committed artifacts reproduce from source.

## Coding conventions

### Python

- Target Python 3.11 or newer.
- Prefer the standard library unless a dependency provides clear product value that cannot be achieved reasonably otherwise.
- Keep lines within the configured 100-character Ruff limit where practical.
- Use type hints for function boundaries and descriptive names for metric variables.
- Preserve atomic write behavior for published artifacts.
- Raise actionable errors at contract boundaries instead of silently coercing invalid data.

### SQL

- State the grain of each mart or query in a comment or its documentation.
- Qualify ambiguous columns and use readable CTE names.
- Protect optional denominators with `NULLIF`.
- Keep metric logic reusable in views rather than duplicating slightly different formulas across queries.
- Treat names such as `revenue_at_risk` as compatibility contracts; document presentation aliases such as unfulfilled value.

### JavaScript and dashboard UI

- Keep the dashboard dependency-free and functional without a backend.
- Escape source-derived strings before inserting HTML.
- Ensure all KPIs, charts, insights, and tables respond to the same filter contract.
- Preserve meaningful labels, table headers, and chart `aria-label` attributes.
- Check an all-data view and at least one warehouse × category incident view after changes.

### Documentation

- Write for the person making an operational or engineering decision.
- Define acronyms on first use.
- Distinguish observed synthetic results, illustrative benchmarks, rules, scenarios, and forecasts.
- Use relative links so documentation works in a repository browser and local checkout.
- Update generated-document templates, not only their current outputs.

## Common change types

### Add or change a source column

Update the entire contract in this order:

1. Generate the field in `src/generate_data.py`.
2. Add it to the ordered CSV header and `TABLE_SPECS` in `src/build_warehouse.py`.
3. Add its SQLite definition and constraints in `sql/01_schema.sql`.
4. Update affected joins or marts in `sql/02_marts.sql`.
5. Update dashboard and report exporters if the field is published.
6. Document the field in `docs/data_dictionary.md`.
7. Add or update tests.
8. Run `make check` and review generated diffs.

### Add or change a metric

Define these before implementation:

- business question;
- analytical grain;
- numerator and denominator;
- unit and display scale;
- date attribution;
- warehouse and category filter behavior;
- zero/null handling;
- benchmark source or illustrative status;
- limitations and possible misuse.

Then update the SQL contract, dashboard calculation, report export, data dictionary, README if material, and tests. A metric must not have different definitions across the dashboard and report.

### Add an analytical mart

- Document its grain and consumers.
- Build it in `sql/02_marts.sql` after dropping the prior view safely.
- Prefer dimensions already governed by the source model.
- Add an integrity or metric-contract test.
- Add the mart to `docs/architecture.md` and `docs/data_dictionary.md`.

### Change synthetic incident patterns

Planted incidents make analytical behavior testable. When changing them:

- document the city, category, period, and intended failure mode;
- preserve a clear comparison window;
- update the incident-detection tests based on an analytically justified signal;
- regenerate the memo, action queue, dashboard data, and screenshots;
- re-check every numeric statement in the README.

### Change the dashboard

1. Run `make dashboard`.
2. Serve `docs/` locally.
3. Verify the all-network view.
4. Verify Bengaluru × Fresh Produce or another intentional incident drill-down.
5. Check the browser console for errors.
6. Confirm tables at narrower viewport widths remain usable.
7. Recapture affected screenshots and run `make test`.

## Tests

Run the full gate before submitting a change:

```bash
make check
```

The suite currently verifies:

- byte-for-byte deterministic generation;
- manifest and database row-count agreement;
- foreign keys and core metric constraints;
- detectability of planted incidents;
- presence and safety of published dashboard and report artifacts;
- README screenshot contracts.

For a focused test run:

```bash
python3 -m unittest tests.test_pipeline.PipelineTest.test_database_integrity_and_metric_contract -v
```

Do not weaken a data-quality or incident assertion merely to accept a source change. Confirm that the updated behavior still satisfies the product contract.

## Pull-request checklist

- [ ] The change has one clear purpose.
- [ ] Metric grain, formula, dates, filters, units, and null behavior remain explicit.
- [ ] Source and generated files are changed together where required.
- [ ] `make check` passes.
- [ ] `git diff --check` passes.
- [ ] The dashboard was manually verified if the UI or analytical extract changed.
- [ ] Screenshots reflect the current dashboard if visible output changed.
- [ ] README, architecture, dictionary, troubleshooting, and security documentation remain accurate.
- [ ] No private, scraped, customer, employee, credential, or confidential data was added.

## Reporting security concerns

Do not open a public issue containing a vulnerability, secret, private dataset, or exploit details. Follow the private reporting guidance in [`SECURITY.md`](SECURITY.md).

# Troubleshooting

This guide covers the common local build and dashboard failures. Run commands from the repository root unless stated otherwise.

## Start with a complete diagnostic run

```bash
python3 --version
make check
```

The project requires Python 3.11 or newer. `make check` regenerates every analytical artifact and runs the full test suite, so its first failing stage usually identifies the responsible layer.

## The dashboard does not open

Start a local static server:

```bash
python3 -m http.server 8000 --directory docs
```

Then open [http://localhost:8000](http://localhost:8000).

### Port 8000 is already in use

Choose another unprivileged port:

```bash
python3 -m http.server 8080 --directory docs
```

Open [http://localhost:8080](http://localhost:8080).

### The page loads without data

If the page says the dashboard data is missing, rebuild the extract:

```bash
make dashboard
```

`make dashboard` also builds its upstream data and warehouse prerequisites. Confirm that `docs/data.js` exists afterward.

### The page shows stale values or styling

Run:

```bash
make dashboard
```

Then perform a normal browser reload. If an old local-server process points at a different checkout, stop it with `Ctrl+C` and restart it from this repository root.

### Opening `docs/index.html` directly behaves differently

The product is designed to work from `file://`, but browser policies and extensions can still affect local files. Use the documented HTTP server command for consistent behavior.

## Build failures

### `python3: command not found`

Install Python 3.11 or newer and verify:

```bash
python3 --version
```

If the executable has a different name, pass it to Make:

```bash
make check PYTHON=python3.12
```

### `make: command not found`

Install GNU Make, or run the equivalent modules in order:

```bash
python3 -m src.generate_data
python3 -m src.build_warehouse
python3 -m src.export_dashboard
python3 -m src.export_report
python3 -m unittest discover -s tests -v
```

### `Missing required input`

The generated CSV layer is absent or incomplete. Run:

```bash
make data
make warehouse
```

Do not hand-edit only one generated CSV: the manifest row counts and cross-table rules are designed to detect partial or inconsistent inputs.

### `schema changed: expected ..., got ...`

The CSV header no longer matches the loader contract in `src/build_warehouse.py`.

If the change is intentional, update these together:

1. `src/generate_data.py`
2. `src/build_warehouse.py`
3. `sql/01_schema.sql`
4. Affected marts and exporters
5. `docs/data_dictionary.md`
6. Tests and committed generated outputs

Then run `make check`.

### `Manifest row counts do not match the CSV inputs`

One or more CSV files were changed without regenerating the manifest. Restore contract consistency with:

```bash
make data
```

If you are testing invalid input handling, keep that mutation inside a test fixture rather than the published source layer.

### A business-rule or foreign-key validation fails

Read the first reported rule and inspect the source relationship it names. Common causes include:

- an order assigned to a warehouse in a different city from its customer;
- a product mapped to a supplier in another category;
- an order labelled successful despite lateness, cancellation, or shortage;
- an order dated before the customer joined;
- a missing parent identifier.

Regenerate the baseline with `make data`, or update the generator and rule intentionally in the same change.

### The warehouse build was interrupted

The builder writes to a temporary database and publishes only after validation. Run:

```bash
make warehouse
```

An interrupted temporary file is safe to replace on the next build. Do not edit the generated SQLite database manually; change the source contract or SQL and rebuild it.

## Test and reproducibility failures

### Deterministic-generation test fails

Check for sources of nondeterminism such as:

- a random call not using the seeded `random.Random` instance;
- unordered set or dictionary iteration affecting output order;
- timestamps based on the current clock;
- locale-dependent formatting;
- platform-dependent line endings.

The generator must produce byte-for-byte identical CSV and manifest files for seed `42`.

### Planted-incident test fails

Changes to generation probabilities, date ranges, order mix, or metric logic may have weakened the expected incident signal. Review the incident definitions in `src/generate_data.py` and the OTIF contract before changing the test threshold.

Do not simply lower the assertion to make the test pass; confirm that the product can still detect the intended operational pattern.

### CI reports committed-output drift

CI rebuilds `data/raw/manifest.json`, `docs/data.js`, and `reports/`, then checks for a diff. Rebuild and review locally:

```bash
make check
git diff -- data/raw/manifest.json docs/data.js reports/
```

Commit intentional output changes alongside their source-code change. If the diff was accidental, fix the nondeterminism or contract mismatch.

### Screenshot contract fails

The README expects these JPEG assets:

- `docs/assets/dashboard-overview.jpg`
- `docs/assets/dashboard-diagnostics.jpg`
- `docs/assets/dashboard-incident.jpg`

Capture screenshots from the rebuilt local dashboard, retain the names above, and run `make test`.

## Cleanup behavior

```bash
make clean
```

This removes only explicitly listed rebuildable files, including generated CSVs, the SQLite database, `docs/data.js`, and report outputs. Some of those outputs are version-controlled so the product can be previewed immediately after cloning.

After cleanup, restore the working product with:

```bash
make setup
```

If you only want to discard local source-code edits, use your version-control workflow. `make clean` is not a substitute for reverting code or documentation changes.

## Still stuck?

Include the following when requesting help:

- operating system;
- `python3 --version`;
- the exact command run;
- the complete first error and traceback;
- whether `make data`, `make warehouse`, or only the browser step fails;
- `git status --short`, after removing any sensitive or unrelated filenames.

Do not publish secrets, credentials, private datasets, or confidential logs. Follow [`../SECURITY.md`](../SECURITY.md) for security-sensitive reports.

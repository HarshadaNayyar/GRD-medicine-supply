# GRD Supply Intelligence

Shared backend for the NESFIC-I-09 medicine supply project: desktop web and React Native Android/iOS clients use one authenticated API and transactional inventory ledger.

**Status:** runnable local integration backend with a labelled Assam synthetic scenario. This is not a measured GRD deployment or the complete web/mobile product. See [PRD status](docs/PRD_STATUS.md) for implemented capabilities and remaining activation gates.

## Run locally

Use Python 3.12 from this repository directory:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
pip install --no-deps -e .
cp .env.example .env
```

Edit `.env`: set a random 32+ character token secret and a strong 12+ character admin password. Never commit this file. Then:

```sh
grd migrate
grd seed-demo --email demo@grd.local --as-of 2026-11-01
grd serve
```

Open **http://127.0.0.1:8011/docs**. Log in at `/api/v1/auth/login`, then use the returned bearer token with the Authorize control. Demo credentials are your configured email/password; no administrator password is hardcoded in source. The seed command prints product/location IDs and refuses to overwrite an existing user.

In a second terminal with the same environment:

```sh
grd worker
```

The API queues forecasts and simulations durably; the worker processes them. `grd worker-once` is useful for a single experiment. Local demo stock is fixed to its declared scenario date; use horizon controls for projections instead of mixing physical balances from different dates.

## What is implemented

- PostgreSQL/SQLite schema and versioned Alembic migrations.
- Hashed passwords, expiring/revocable bearer tokens and server-enforced organisation/role/location scope.
- Product identity, base/pack conversions, scoped network locations and approved-route parameters.
- Batch ledger, FEFO reservations, holds, expiry writeoffs, counts, corrections, returns pending review and reconciliation.
- Versioned plans, approval, partial dispatch/receipt, damage cases and cancellation that preserves goods in transit.
- Stable idempotency keys for stock commands: duplicate mobile retries do not duplicate stock.
- Pack, route, donor-protection, shelf-life, maximum-order, budget and destination-capacity checks; expiry rescue and finite-stock draft allocation.
- Scoped GeoJSON plus matching map table with shortages, coverage, expiry exposure, provenance and freshness.
- CSV/XLSX demand preview/import, source manifests and duplicate prevention.
- Baselines/initial ML, chronological selection and recursive multi-horizon evaluation, residual uncertainty and explicit missing/stale-history states.
- Reproducible paired policy simulation with conservation checks and honest trade-offs.
- Two grounded, non-mutating assistant modes: recorded plan facts and approved policy excerpts.
- Durable job status/cancel/recovery, health endpoints, container definitions, CI and a shared TypeScript client transport.

These are API capabilities. The actual website and native app, device testing, push-provider integration and company-data activation are not included in this backend handover.

## Recommended demo

Pick Silchar and the paracetamol demo presentation on `/network`. Create a request, inspect `/planning/options` or `/planning/expiry-rescue`, propose a transfer from the Guwahati demo distributor, approve it, dispatch, receive in two parts and quarantine a damaged portion. Refresh the map, request fulfilment, cases and reconciliation. Then show an overcommitted or held-batch action being rejected. Use an offline event's same key/body when replaying it.

The current local database also contains a compressed synthetic walkthrough and two completed evidence jobs; IDs are in the ignored `data/demo-walkthrough.json`. This file is a local convenience, not a portable source fixture. Regenerate on a fresh database using the seed and documented API journey.

## Data honesty

The seed creates **18,375 synthetic demand rows** across 5 fictional operating locations and 5 illustrative products. Approximate Assam town coordinates are not GRD facility locations. Stock, orders, seasonal effects, prices and routes are assumptions, not observed company operations.

Real NASA POWER weather context has a separate reproducible download. The original public pharmacy benchmark remains an eight-category series with its original provenance. Redistributing it across Assam or assigning it invented presentations creates synthetic data; it does not produce observed regional demand. See [data strategy](docs/DATA_STRATEGY.md).

```sh
python scripts/fetch_public_data.py pharma-benchmark
python scripts/fetch_public_data.py weather
```

Dataset files and databases are ignored by Git. Follow source licences before any commercial pilot. No private GRD data or policy has been assumed.

## Original team's experiments

The original notebook and scripts are retained as experiment entry points. The old dashboard PDF is a historical export and must not be reused as current evaluation evidence without regeneration. Scripts 05/06/08 now delegate to corrected shared adapters. The category catalogue no longer presents broad ATC sales as verified individual medicines. The baseline simulator is still a declared synthetic experiment with assumed external supply, not the finite-stock operational service.

Extract `salesdaily.csv` from the downloaded benchmark ZIP, then run:

```sh
grd legacy-run --source data/external/salesdaily.csv --output data/legacy-run --as-of 2019-09-05
```

This prepares cleaned inputs and runs 02–08 in order under a separate output directory. Forecast results include horizon-specific evidence rather than pretending a one-week assessment validates four-week recursion. The CSV transfer adapter shares a donor allocation budget. Shortage projection includes empty-stock combinations and refuses a stale snapshot. `grdmedicine.sql` is an old manual-MySQL exploration file; do not use it to initialise the backend. Use Alembic.

## Verification and deployment

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 pytest -q
ruff check grd tests scripts
grd migrate
alembic check
```

PostgreSQL integration tests rebuild a dedicated database named `grd_test`; never point them at company/shared data. See [operations](docs/OPERATIONS.md) for containers, worker recovery and backup/restore, and [verification](docs/VERIFICATION.md) for executed checks and limitations.

- [API snapshot](docs/openapi.json)
- [Website / React Native integration](docs/CLIENT_INTEGRATION.md)
- [PRD traceability](docs/PRD_STATUS.md)
- [Data strategy](docs/DATA_STRATEGY.md)

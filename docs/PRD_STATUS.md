# PRD backend traceability and activation gates

Reference: final product PRD v1.0, 23 October 2026. This backend is a runnable integration release, not a claim that every product acceptance gate or company pilot has passed.

| Area | Implemented | Remaining activation/depth |
|---|---|---|
| Data foundation | CSV/XLSX demand preview, row errors, atomic imports, duplicate prevention, source metadata, integer units and exact pack conversions | Approved GRD schema and unit mapping; automated ERP feeds; versioned correction/replacement UI |
| Forecasting | Baselines including intermittent demand, initial ML candidate, validation selection, separated final targets, recursive 1–4 week evaluation, residual intervals and measured coverage, short-history/stale fallbacks | Local seasonal-signal ablation requires aligned local demand; broader backtesting/calibration; real demand-censoring inference |
| Stock integrity | Transactional SQL, immutable movements, nonnegative stock, FEFO reservations, holds, explicit counts/adjustments/reversals, reconciliation, competing-approval tests | Operational user acceptance, retention rules and real source reconciliation |
| Planning | Finite donor availability/protection, permissions, packs, arrival shelf life, costs/budgets, per-product destination capacity, rejected options, expiry rescue, recent published forecast integration | Multi-donor/global optimisation, configurable owner-approved priorities beyond the implemented earliest-due-date finite-stock allocation, real vendor reliability and approved commercial rules |
| Execution | Requests, versioned proposals, scoped approvals, partial dispatch/receipt, damage quarantine, cancellation, return receipt pending disposition, audit | In-transit return transport workflow; external purchase-order acknowledgement and vendor integration; full recall-case management outside PRD boundary |
| Map and web integration | React workspace with interactive Assam map, linked table, medicine/location/horizon/layer filters, stock evidence, action queue, plan/receipt controls, batch register, import preview, forecast/simulation charts, assistant and audit; keyboard focus and responsive browser QA | Full offline web operation, broader assistive-technology/user acceptance checks, production performance and hosted deployment |
| React Native | Expo SDK 58 client with five tabs, bundled vector map, shared action ranking, source comparison, scoped approval/dispatch/partial receipt, verified internal QR/manual lookup, count snapshot guard, native secure tokens and bounded persistent outbox, evidence/assistant/activity | Native build/device QA (see MOBILE_DEMO.md), signed distribution, full offline cold start, automatic background sync and push delivery |
| Collaboration | Cases, assignment, comments, due dates, resolution, scoped audit | Notification outbox/provider adapters, escalation scheduler and attachment storage |
| Assistance | Two non-mutating grounded modes: recorded plan evidence and approved policy excerpts | Improved search/optional LLM answer synthesis, adversarial provider tests and owner-approved real policy corpus |
| Evidence | Paired reproducible lane simulator, conservation checks, forecast job provenance and cut-offs | Network-wide policy replay, real pilot baseline/outcomes, expiry observation window and approved cost valuation |
| Deployment | Alembic migrations, PostgreSQL and SQLite, durable jobs/cancel/recovery, health/container/CI definitions, Render Free blueprint with supervised API/worker, optional Vercel frontend, managed-Postgres requirement and locally verified cloud startup/restart | Public account setup/deployment, target-container memory/cold-start checks, hosted secrets/monitoring/rate limits, restore drill and operational incident plan |

## Release discipline

Do not present this as a finished industry deployment or the complete competition product. Run a supervised synthetic demo, finish native device validation/distribution and remaining acceptance evidence, then activate company data/policies in shadow mode before live stock decisions. A missing advantage over a simple baseline is reported honestly; the model is not chosen to satisfy a headline percentage.

Suggested next additions: a clear reconciliation inbox; scanned batch receipt with partial damage; a map that explains why an attractive-looking transfer is rejected; and a scenario comparison that exposes added inventory/cost as well as improved service. These should share the same backend records.

# Alembic Migration Idempotency & Schema Drift Fixes

_Last updated: 2026-06-07_

This document explains a set of changes made to fix recurring database errors
during startup and organization setup, and to make Alembic migrations safe to
re-run against existing databases.

---

## 1. The core problem

Several databases in dev were **restored from older backups** and then
**stamped forward** (`alembic stamp`) to skip migrations that crashed with
`DuplicateTable` / `DuplicateColumn` errors. Stamping marks migrations as
applied **without running them**, so newer tables/columns were never created.

This produced two failure modes:

1. **Migrations crash on re-run** — e.g. `CREATE TYPE`, `create_table`,
   `add_column` failing because the object already existed.
2. **Schema drift** — the DB was missing tables/columns that the models
   expected, causing runtime `500`/`503` errors such as:
   - `column organizations.parent_organization_id does not exist`
   - `column item_groups.default_valuation_method does not exist`
   - `relation "notifications" does not exist`

---

## 2. Centralized migration idempotency (main fix)

Instead of hand-editing ~363 `create_*` calls across 47 migration files, a
single **idempotency layer** wraps Alembic's create operations once and applies
to **every** migration — existing and future.

### Files

- `core-service/alembic/idempotent_ops.py`
- `identity-service/alembic/idempotent_ops.py`
- Wired into `run_migrations_online()` in both `core-service/alembic/env.py`
  and `identity-service/alembic/env.py` (just before `context.run_migrations()`).

### What it makes idempotent (skips if the object already exists)

- `op.create_table`
- `op.create_index`
- `op.add_column`
- `op.create_unique_constraint`
- `op.create_foreign_key`
- `op.create_check_constraint`
- `op.create_primary_key`
- Raw `op.execute("CREATE TYPE ... AS ENUM ...")` → auto-wrapped in an
  `IF NOT EXISTS` guard (catches unguarded enums in migrations `049` and `051`).

### How it works

`apply_idempotent_patches()` monkeypatches the `alembic.op` helpers at runtime.
Each wrapper uses SQLAlchemy's `inspect(op.get_bind())` to check existence
before delegating to the original function. When something is skipped you'll see
a log line like:

```
[idempotent] table 'notifications' exists — skipping create_table
[idempotent] column 'item_groups.default_valuation_method' exists — skipping add_column
```

### Why this approach

- One place to maintain instead of 47 files.
- Cannot "miss" a case — covers all current and future migrations.
- Drops are intentionally **not** guarded (only create-style ops).

### Caveats / limitations

- **Data `INSERT`s are NOT deduplicated** — this only guards schema (DDL).
  Do **not** `alembic stamp base` + full re-run on a populated DB, or seed
  rows may duplicate.
- An enum type created *implicitly* inside a brand-new `create_table` is not
  guarded (rare edge: table missing but type already exists). Explicit
  `op.execute("CREATE TYPE ...")` cases are covered.

### Result

`alembic upgrade head` now runs from any state without
`DuplicateTable`/`DuplicateColumn`/`DuplicateObject` errors — no more manual
stamping needed.

---

## 3. Schema reconciliation migration (core-service)

`core-service/alembic/versions/057_reconcile_schema_with_models.py`

A forward-only, idempotent migration that brings any drifted DB back in line
with the current models **without touching data**:

1. Ensures every PostgreSQL ENUM type referenced by the models exists.
2. `Base.metadata.create_all(checkfirst=True)` — creates any missing tables
   (e.g. `notifications`).
3. Adds any missing columns to existing tables as **NULLABLE** (each column in
   its own SAVEPOINT, so one failure can't abort the run).

This is what repairs `item_groups.default_valuation_method`, the `notifications`
table, and any other missing columns in one pass.

### Hardening (after a crash on first run)

`057` originally used `Base.metadata.create_all(...)` and `sorted_tables`, both of
which perform a **global foreign-key sort** over the entire metadata. That sort
raised `NoReferencedTableError` and aborted the whole migration because the
`PickList` model (`pick_lists`) was **not imported** in `app/models/__init__.py`,
while `dispatch_records` / `gate_verification` / `delivery_note` reference it.

Two fixes:

1. **Root cause** — added the missing import to `core-service/app/models/__init__.py`:
   `from app.models.pick_list import PickList, PickListItem` (and added both to
   `__all__`). Now the FK target exists in `Base.metadata`.
2. **Defense in depth** — `057` no longer relies on the global sort. It creates
   missing tables one-by-one (`_create_missing_tables`) over multiple passes,
   each in its own SAVEPOINT, and iterates `metadata.tables.values()` (unordered)
   when adding columns. A single unresolved FK can no longer abort the run; it is
   logged (`[057] Skipped table ...`) and skipped.

---

## 4. Identity-service missing columns migration

`identity-service/alembic/versions/014_add_missing_organization_billing_columns.py`

The `Organization` model declared columns that **no migration ever created**
(they only existed in backup-restored DBs). This migration idempotently adds
them to the `organizations` table:

- `trial_end_date`, `max_users`, `max_credits`, `billing_contact_email`,
  `billing_cycle`, `customer_since`, `last_billed_date`, `next_billing_date`
- `parent_organization_id` (+ self-referential FK `fk_organizations_parent_organization_id`)

This fixed the `500 DATABASE_ERROR` when creating an organization
(`column organizations.parent_organization_id does not exist`).

### Related: better error logging

`identity-service/app/main.py` — the `SQLAlchemyError` handler previously
swallowed the real error and returned a generic `DATABASE_ERROR`. It now logs
the full exception/traceback so the actual failing column/constraint is visible
in the container logs.

---

## 5. AI module feature flag (visibility control)

The AI Hub tab is hidden by default for **all** users (including admins/owners)
until an administrator enables it.

### Backend

- `core-service/app/core/constants.py` — added `AI_MODULE_ENABLED = "ai_module_enabled"`.
- `core-service/alembic/versions/056_seed_ai_module_feature_flag.py` — seeds the
  GLOBAL flag with `enabled=false, visible=false` (idempotent; never overwrites).

### Frontend

- `libs/shared/ui/src/constants/constants.ts` — added
  `AI_MODULE_ENABLED = 'ai_module_enabled'`.
- `apps/inventory/src/app/app.tsx` — the AI Hub nav item and view render only
  when `useFeatureVisibility('ai_module_enabled')` returns `visible=true`
  (deny-by-default).

---

## 6. Master organization setup idempotency

`core-service/create_master_organization.py`

The startup B2B setup did an `INSERT ... ON CONFLICT (id)` for a hardcoded
canonical master id (`550e8400-...001`). On a **restored backup** a master org
already existed with a **different id**, so the conflict never matched, the
script tried to INSERT a *second* master, and the `check_single_master_org()`
trigger raised `Only one master organization is allowed`.

Fix: before inserting, look for any existing `organization_type = 'master'`
row. If one exists (any id), **adopt and normalise it** (`update_master_organization`)
and use its id for all downstream steps. The canonical row is only inserted
when no master exists at all. (`result.id` references were replaced with the
resolved `master_id`.)

---

## 7. How to apply everything

Normal startup now runs all migrations safely:

```bash
docker compose up --build
```

If you need to run migrations manually for a single service:

```bash
docker compose up -d postgres
docker compose run --rm --no-deps --entrypoint "" core-service python -m alembic upgrade head
docker compose run --rm --no-deps --entrypoint "" identity-service python -m alembic upgrade head
```

Watch for `[idempotent] ... skipping` and `[057] Added missing column ...` log
lines to confirm what was skipped vs. repaired.

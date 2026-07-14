# Feature Flag Developer Guide

This guide covers how to create, integrate, and manage feature flags in Horizon Sync ERP.

## Overview

Feature flags give admins two levels of runtime control over any feature — without redeployment:

| Field       | Default | Purpose                                                    |
|-------------|---------|-------------------------------------------------------------|
| `enabled`   | `false` | Controls whether the feature works. When off, API returns 423 and UI shows "feature disabled" banner. |
| `visible`   | `true`  | Controls whether the feature's UI tab/nav appears at all. When off, the tab is completely hidden. |

## Naming Convention

All flag names must follow `snake_case` format: lowercase letters, numbers, and underscores only.

**Pattern:** `{module}_{sub_feature}` or `{module}_enabled`

| Type | Example | Description |
|------|---------|-------------|
| Module-level gate | `invoices_enabled` | Gates the entire invoices module |
| Sub-feature gate | `invoice_auto_journal_posting` | Gates a specific behavior within invoices |
| New feature rollout | `payments_bulk_import` | Gates a new capability being rolled out |

**Rules:**
- Use `_enabled` suffix for module-level flags that gate an entire feature
- Use descriptive names for sub-feature flags (no `_enabled` suffix needed)
- Keep names under 50 characters
- Never use spaces, hyphens, or uppercase letters
- Regex validation: `^[a-z0-9_]+$`

## Step-by-Step: Adding a New Feature Flag

### Step 1: Add the constant

Add your flag name to `app/core/constants.py`:

```python
# Payments module
PAYMENTS_ENABLED = "payments_enabled"
PAYMENTS_BULK_IMPORT = "payments_bulk_import"
```

### Step 2: Seed the flag in the database

Via admin UI (Feature Controls page) or SQL:

```sql
INSERT INTO feature_flags (id, name, description, enabled, visible, scope, created_at, updated_at)
VALUES (gen_random_uuid(), 'payments_enabled', 'Gates the entire payments module', true, true, 'GLOBAL', NOW(), NOW())
ON CONFLICT ON CONSTRAINT uq_feature_flag_scope DO NOTHING;
```

### Step 3: Backend integration

**Option A — Gate an entire router (all endpoints):**

```python
from fastapi import APIRouter, Depends
from app.dependencies import require_feature_flag
from app.core.constants import PAYMENTS_ENABLED

router = APIRouter(dependencies=[Depends(require_feature_flag(PAYMENTS_ENABLED))])
```

When the flag is disabled, all endpoints on this router return HTTP 423:
```json
{
  "code": "FEATURE_DISABLED",
  "feature": "payments_enabled",
  "message": "Feature 'payments_enabled' is currently disabled by your administrator."
}
```

**Option B — Gate a specific code path within a service:**

```python
from app.services.feature_flag_service import is_feature_enabled
from app.core.constants import PAYMENTS_BULK_IMPORT

class PaymentService:
    def process(self, db):
        if is_feature_enabled(PAYMENTS_BULK_IMPORT, db):
            # new behavior
        else:
            # default behavior or skip
            logger.info("Skipping bulk import — feature flag disabled")
```

**Option C — Check visibility from backend:**

```python
from app.services.feature_flag_service import is_feature_visible

if is_feature_visible("payments_enabled", db):
    # feature is visible in UI
```

### Step 4: Frontend integration

**Hide/show a navigation tab based on visibility:**

```tsx
import { useFeatureVisibility } from '../hooks/useFeatureVisibility';

export function MyPage() {
  const paymentsFlag = useFeatureVisibility('payments_enabled');

  return (
    <nav>
      {paymentsFlag.visible && (
        <NavItem label="Payments" ... />
      )}
    </nav>
  );
}
```

**Show "feature disabled" banner when enabled=false:**

In your data-fetching hook, detect the 423 response:

```typescript
const handleFetchError = (err: unknown) => {
  const apiErr = err as { status?: number; details?: { detail?: { code?: string } } };
  if (apiErr?.status === 423 && apiErr?.details?.detail?.code === 'FEATURE_DISABLED') {
    setError('FEATURE_DISABLED');
  } else {
    setError('Failed to load data');
  }
};
```

Then in your component (after all hooks):

```tsx
if (error === 'FEATURE_DISABLED') {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <Lock className="h-8 w-8 text-muted-foreground mb-4" />
      <h2>Feature Not Available</h2>
      <p>This feature is currently disabled by your administrator.</p>
    </div>
  );
}
```

## Safe Defaults

| Helper | Returns on error | Rationale |
|--------|-----------------|-----------|
| `is_feature_enabled(name, db)` | `False` | Disable the feature if unsure — prevents unintended behavior |
| `is_feature_visible(name, db)` | `True` | Show the feature if unsure — prevents UI from breaking |
| `useFeatureVisibility(name)` | `{ visible: true, enabled: true }` | Same principle on frontend |

## API Endpoints

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `GET /api/v1/feature-flags/evaluate/{name}` | Any authenticated user | Check flag status (used by frontend) |
| `GET /api/v1/admin/feature-flags` | Admin only | List all flags |
| `POST /api/v1/admin/feature-flags` | Admin only | Create flag |
| `PATCH /api/v1/admin/feature-flags/{id}` | Admin only | Update flag |
| `DELETE /api/v1/admin/feature-flags/{id}` | Admin only | Delete flag |

## Evaluate Response Shape

```json
{
  "feature_name": "invoices_enabled",
  "enabled": true,
  "visible": true
}
```

## Key Files

| File | Purpose |
|------|---------|
| `app/core/constants.py` | Flag name constants — add new flags here |
| `app/models/feature_flag.py` | SQLAlchemy model |
| `app/schemas/feature_flag.py` | Pydantic schemas |
| `app/services/feature_flag_service.py` | Service + `is_feature_enabled` / `is_feature_visible` helpers |
| `app/dependencies.py` | `require_feature_flag()` router dependency |
| `app/api/v1/endpoints/feature_flag_evaluate.py` | Public evaluate endpoint |
| `app/api/v1/endpoints/admin/feature_flags.py` | Admin CRUD endpoints |
| `apps/inventory/src/app/hooks/useFeatureVisibility.ts` | Frontend hook |

## Checklist for New Flags

- [ ] Add constant to `app/core/constants.py`
- [ ] Seed the flag in the database (SQL or admin UI)
- [ ] Backend: add `require_feature_flag()` dependency or `is_feature_enabled()` check
- [ ] Frontend: add `useFeatureVisibility()` hook if tab hiding is needed
- [ ] Frontend: handle 423 `FEATURE_DISABLED` response in error handler if using `enabled` gating
- [ ] Test with flag enabled, disabled, and hidden
- [ ] Verify safe defaults work (flag missing from DB should not break anything)

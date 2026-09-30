# Internal Service-to-Service Secret

The identity-service calls a handful of core-service "internal" endpoints during
organization onboarding:

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/internal/warehouse-users` | Assign a worker to a warehouse |
| `POST /api/v1/setup/organization-defaults` | Seed default master data for a new org |
| `POST /api/v1/setup/default-chart-of-accounts` | Create default chart of accounts |

These endpoints are guarded by a shared secret sent in the `X-Internal-Secret`
header. The identity-service signs requests with it, and core-service verifies it
with a constant-time comparison (`secrets.compare_digest`).

## Settings

| Service | Secret field | Secrets-Manager field | Region field |
|---|---|---|---|
| core-service | `internal_service_secret` | `internal_service_secret_id` | `aws_region` |
| identity-service | `core_service_secret` | `core_service_secret_id` | `aws_region` |

**Both services must use the same secret value.**

## Resolution order

At startup, the secret is resolved in this order:

1. **AWS Secrets Manager** — only when `*_secret_id` is set (see AWS below).
2. **Environment variable** — `INTERNAL_SERVICE_SECRET` (core) / `CORE_SERVICE_SECRET` (identity).
3. **Test default** — `dev-internal-secret-testing` (local development only).

If Secrets Manager is configured but the fetch fails (or `boto3` is missing), it
logs a warning and falls back to the environment/default value — it never
silently breaks startup.

## Test default

The current default is:

```
dev-internal-secret-testing
```

This is a **placeholder for testing only**. Replace it before production:

- **AWS**: create a secret in AWS Secrets Manager and set `*_secret_id`.
- **Railway / other clouds**: set `INTERNAL_SERVICE_SECRET` / `CORE_SERVICE_SECRET`
  to a strong random value.

## Environment setup

### Local development

No action needed — the test default applies. `docker-compose.yml` also defaults
`CORE_SERVICE_SECRET` to the same value.

### AWS (production)

```bash
# core-service
INTERNAL_SERVICE_SECRET_ID=my/internal-service-secret   # Secrets Manager name or ARN
AWS_REGION=ap-south-1

# identity-service
CORE_SERVICE_SECRET_ID=my/internal-service-secret        # same secret
AWS_REGION=ap-south-1
```

The value is fetched once at startup. `boto3` is already a dependency of
core-service and was added to identity-service's `requirements.txt`.

To pick up a rotated secret, restart the service (the value is read at startup).

### Railway / other non-AWS clouds (dev & stage)

Don't set `*_secret_id`. Just set the plain variables:

```bash
# core-service
INTERNAL_SERVICE_SECRET=stage-internal-secret

# identity-service
CORE_SERVICE_SECRET=stage-internal-secret
```

Railway tip: define the secret once as a shared variable and reference it from
both services so the value lives in one place.

### Remote docker-compose

`docker-compose.remote.yml` makes the variable **required** (fails fast if
unset):

```yaml
CORE_SERVICE_SECRET: ${CORE_SERVICE_SECRET:?CORE_SERVICE_SECRET must be set}
```

## Fail-closed behaviour

- If the secret is empty, core-service's `require_internal_service` returns
  `503` for internal endpoints (onboarding calls fail, they don't silently pass).
- At startup, core-service **fails fast** in `production` and logs a warning in
  other environments when the secret is empty (see `app/main.py` lifespan).

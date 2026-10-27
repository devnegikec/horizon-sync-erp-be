# Object storage (Railway bucket) — dev and stage

S3-compatible storage for QR workbooks, Product images, and inbound-exception
evidence. Railway calls these **buckets**; they are created per project and
deployed to an environment.

## Bucket layout

Every object lives under a per-organization folder named after the
organization **slug**:

```
orgs/<org-slug>/
├── qseal/
│   └── products/<product_id>/
│       ├── blocks/<block_id>/qr_codes.xlsx
│       └── images/{logo|banner}/<32-hex>.{jpg|png|webp}
└── inbound/
    └── exceptions/<exception_id>/evidence/<32-hex>.{jpg|png|webp|pdf}
```

- Slug lookup: `GET /api/v1/identity/internal/organizations/{id}/slug`
  (header `X-Internal-Secret`), cached in-process for 5 minutes
  (`core-service/app/services/organization_directory.py`).
- If identity-service is unreachable the key falls back to
  `orgs/org-<organization_id>/...` so uploads never fail.
- Keys written before this layout (`qseal/organizations/<uuid>/...`,
  `inbound/organizations/<uuid>/...`) are still readable/deletable — the
  stored key is what the API validates against, and both patterns are accepted.
- Renaming an organization slug does **not** move existing objects; stored
  keys keep resolving, new writes go to the new folder.

## Environment variables

Set on `core-service`, `qr-worker` and `core-worker` (all three can write
objects). Never commit the keys.

| Variable                          | Value                                                                                        |
| --------------------------------- | -------------------------------------------------------------------------------------------- |
| `AWS_S3_BUCKET`                   | bucket name (Railway appends a suffix: `brandwise-dev-files` → `brandwise-dev-files-iywczu`) |
| `AWS_S3_REGION`                   | bucket region (`sjc`, `iad`, `ams`, `sin`); credentials report `auto`                        |
| `AWS_S3_ENDPOINT_URL`             | endpoint from `railway bucket credentials --json` (dev: `https://t3.storageapi.dev`)         |
| `AWS_ACCESS_KEY_ID`               | `accessKeyId`                                                                                |
| `AWS_SECRET_ACCESS_KEY`           | `secretAccessKey`                                                                            |
| `AWS_S3_ADDRESSING_STYLE`         | `virtual` for `urlStyle: virtual-host` (dev), `path` when credentials report `path`          |
| `AWS_S3_SERVER_SIDE_ENCRYPTION`   | `none` for Railway buckets (they reject the AWS SSE header); `AES256` on AWS                 |
| `AWS_S3_PRESIGNED_EXPIRY_SECONDS` | optional, default 300                                                                        |

`identity-service` additionally needs `INTERNAL_SERVICE_SECRET` set to the same
value as core-service's (`X-Internal-Secret`), used by the slug endpoint.

## Provisioning (dev) — DONE 2026-10-27

The dev bucket `brandwise-dev-files` (id `19e2b099-453e-49d9-b336-d70bd6b19c46`)
exists in project BW-2.0, environment `dev`, region `sin`. Its S3 bucket name is
`brandwise-dev-files-iywczu`, endpoint `https://t3.storageapi.dev`, region
`auto`, addressing style `virtual-host`. `AWS_S3_*` was set on `core-service`,
`qr-worker` and `core-worker`; `INTERNAL_SERVICE_SECRET` on `identity-service`.
Put/get/presign/delete was verified directly against the bucket.

```bash
railway login                      # interactive, once per machine

# 1. Bucket (project BW-2.0, environment dev)
railway bucket create brandwise-dev-files --region sin -e dev --json

# 2. S3 credentials
railway bucket credentials -b brandwise-dev-files -e dev --json
# -> endpoint, accessKeyId, secretAccessKey, bucketName, region, urlStyle

# 3. Wire variables (repeat --service for core-service, qr-worker, core-worker)
railway variable set \
  AWS_S3_BUCKET=brandwise-dev-files \
  AWS_S3_REGION=sin \
  AWS_S3_ENDPOINT_URL=https://<endpoint> \
  AWS_ACCESS_KEY_ID=<key> \
  AWS_SECRET_ACCESS_KEY=<secret> \
  AWS_S3_ADDRESSING_STYLE=path \
  AWS_S3_SERVER_SIDE_ENCRYPTION= \
  --service core-service -e dev --skip-deploys

# 4. Slug endpoint secret (identity-service)
railway variable set INTERNAL_SERVICE_SECRET=<same-as-core> \
  --service identity-service -e dev --skip-deploys
```

Then redeploy `identity-service` (new endpoint) and `core-service` (new key
layout), followed by the workers.

## Smoke test

1. Upload a Product logo → confirm the object key starts with
   `orgs/<slug>/qseal/products/<id>/images/logo/`.
2. Generate a QR block → download it → the presigned URL resolves.
3. Re-upload/replace a logo → old object is deleted.

## Backups / access

```bash
# one-off mirror to local disk
AWS_ACCESS_KEY_ID=<key> AWS_SECRET_ACCESS_KEY=<secret> \
aws --endpoint-url https://<endpoint> s3 sync \
  s3://brandwise-dev-files/ ./backup/brandwise-dev-files/

# nightly mirror (rclone keeps an S3-compatible remote)
rclone sync rw-dev:brandwise-dev-files ./backup/brandwise-dev-files --fast-list
```

Railway buckets do not provide versioning/object-lock, so keep at least one
out-of-provider copy (S3/R2/local) for anything that matters.

## Stage rollout

1. Validate dev end-to-end (upload, generate, download, delete).
2. Create `brandwise-stage-files` with `railway bucket create ... -e staging`
   (or the actual environment name) and repeat the variable wiring.
3. Deploy `identity-service` before `core-service` so the slug endpoint exists.
4. Existing AWS S3 objects are untouched; either copy them into the new bucket
   (`aws s3 sync s3://old-bucket s3://brandwise-stage-files`) or leave them and
   keep serving through the old credentials until migrated.

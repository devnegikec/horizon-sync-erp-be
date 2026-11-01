# Profile Image (Avatar) API — identity-service

Users can upload, replace and remove their own profile photo. `users.avatar_url`
already existed in the schema, so **no migration is required**.

Base path: `/api/v1/identity` (identity-service).

## Endpoints

### 1. Upload / replace — `POST /users/me/avatar`

`multipart/form-data`, field name **`file`**. Auth: any logged-in user (no
permission required — it only touches the caller's own row).

```bash
curl -X POST https://dev-identity-api.ciphercode.ai/api/v1/identity/users/me/avatar \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@avatar.png;type=image/png"
```

Response `200` — the full profile, including the new URL:

```json
{
  "id": "…",
  "email": "…",
  "avatar_url": "https://dev-identity-api.ciphercode.ai/api/v1/identity/users/avatars/users/<uuid>/avatars/<32-hex>.png"
}
```

Replacing an image deletes the previous file, so old avatars do not accumulate.

| Status | When |
|---|---|
| `415` | content type is not `image/png`, `image/jpeg`, `image/webp` |
| `422` | empty file |
| `413` | larger than `AVATAR_MAX_BYTES` (default 2 MB) |
| `503` | storage backend unavailable |

### 2. Remove — `DELETE /users/me/avatar`

```bash
curl -X DELETE https://dev-identity-api.ciphercode.ai/api/v1/identity/users/me/avatar \
  -H "Authorization: Bearer $TOKEN"
```

Clears `avatar_url` and deletes the stored file.

### 3. Read — `GET /users/avatars/{key}`

Public, unauthenticated, `Cache-Control: public, max-age=86400`. This is the
`avatar_url` returned above. Only keys matching
`users/<uuid>/avatars/<32-hex>.(jpg|png|webp)` are servable, so traversal and
arbitrary object reads are rejected with `404`.

### 4. Set an already-hosted image — `PATCH /users/me`

```json
{ "avatar_url": "https://cdn.example.com/team/priya.png" }
```

`avatar_url` must be an absolute `http(s)` URL. Because the partial update
ignores `null`, use `DELETE /users/me/avatar` to clear it.

## Frontend notes

- Send `FormData` and let the browser set the multipart boundary. Do **not**
  set `Content-Type` manually.
- Validate type/size client-side before uploading (2 MB, PNG/JPEG/WebP) so the
  user gets instant feedback.
- `avatar_url` is returned by login, `/identity/me`, `PATCH /users/me` and both
  avatar endpoints — refresh the cached user after any of them.
- Render with `referrerpolicy="no-referrer"` and an initials fallback when
  `avatar_url` is `null`.

## Storage

`app/services/avatar_storage.py`:

1. **S3-compatible bucket** when `AWS_S3_BUCKET` is set (same variable names as
   core-service). The bucket may stay private — files are proxied through
   `GET /users/avatars/{key}`.
2. **Local directory** `AVATAR_STORAGE_DIR` (default `identity-service/media/avatars`)
   otherwise. A warning is logged: container filesystems are ephemeral, so
   uploads disappear on redeploy.

To make dev/staging durable, copy the core-service bucket variables onto the
identity-service. **Configured on both `dev` and `staging`** (2026-11-01):

| Variable | dev | staging |
|---|---|---|
| `AWS_S3_BUCKET` | `brandwise-dev-files-iywczu` | `brandwise-stage-files-zufa6s` |
| `AWS_S3_REGION` | `auto` | `sin` |
| `AWS_S3_ENDPOINT_URL` | `https://t3.storageapi.dev` | same |
| `AWS_S3_ADDRESSING_STYLE` | `virtual` | same |
| `AWS_S3_SERVER_SIDE_ENCRYPTION` | `none` | same |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | copied from core-service | copied from core-service |
| `MEDIA_BASE_URL` | `https://dev-identity-api.ciphercode.ai` | `https://identity-api.ciphercode.ai` |

> Railway bucket names carry a random suffix (`brandwise-stage-files-zufa6s`).
> core-service `staging` still has the suffix-less `brandwise-stage-files`, which
> returns `NoSuchBucket` — image uploads there are broken until corrected.

Avatars live under the `users/` key prefix, which core-service never uses, so
the two services can share one bucket without colliding.

Optional: `MEDIA_BASE_URL` to force the absolute base used in `avatar_url`
(otherwise it is derived from the incoming request, which honours
`X-Forwarded-*`). Set to `https://dev-identity-api.ciphercode.ai` on `dev`.

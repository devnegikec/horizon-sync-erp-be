# API Endpoints

Base path: `/api/v1/`

All endpoints require `Authorization: Token <token>` unless marked **Public**.

---

## Authentication

| Method | Path                 | Auth     | Description          |
| ------ | -------------------- | -------- | -------------------- |
| POST   | `auth/login/`        | Public   | Login, returns token |
| POST   | `auth/logout/`       | Required | Invalidate token     |
| POST   | `auth/web_register/` | Public   | Register new user    |
| POST   | `sent-otp/`          | Public   | Send email OTP       |
| POST   | `otp/`               | Public   | Verify email OTP     |
| POST   | `verify-otp/`        | Public   | Verify OTP (generic) |
| POST   | `send_mobileotp/`    | Public   | Send mobile OTP      |
| POST   | `verify_mobileotp/`  | Public   | Verify mobile OTP    |
| GET    | `` (root)            | Public   | BrandwiseSpace login |

---

## Products & QR

| Method   | Path                      | Description                               |
| -------- | ------------------------- | ----------------------------------------- |
| GET/POST | `products/`               | List / create products                    |
| POST     | `generate/product-block/` | Generate QR code blocks for a product     |
| POST     | `product/activate/`       | Activate a QR code                        |
| GET/POST | `product/qr_settings/`    | Get or set QR activation parameters       |
| GET      | `qr_settings/`            | QR settings (alternate endpoint)          |
| GET      | `product/qr_scans/`       | Scan analytics for a product              |
| GET      | `product/expiry/`         | Product expiry tracking                   |
| POST     | `validate/product-block/` | Authenticate a product (anti-counterfeit) |
| POST     | `authentication/`         | Product authentication check              |

---

## Orders

| Method   | Path           | Description                 |
| -------- | -------------- | --------------------------- |
| GET/POST | `order/`       | List / create orders        |
| GET/POST | `productitem/` | List / create product items |

---

## Coupons

| Method | Path                   | Description                                   |
| ------ | ---------------------- | --------------------------------------------- |
| POST   | `coupon-verification/` | Verify a coupon code                          |
| POST   | `coupon-redeem/`       | Redeem a coupon (records final_billed_amount) |
| POST   | `coupon-unlock/`       | Unlock a coupon (logs to CouponUnlockLog)     |

---

## Feedback & Surveys

| Method   | Path                | Description              |
| -------- | ------------------- | ------------------------ |
| POST     | `feedback/`         | Submit campaign feedback |
| GET/POST | `feedbackview/`     | Feedback viewset         |
| GET/POST | `surveysubmitview/` | Submit survey response   |
| GET/POST | `surveylistview/`   | List surveys             |

---

## Warranty

| Method | Path               | Description                     |
| ------ | ------------------ | ------------------------------- |
| POST   | `warranty/`        | Register warranty               |
| POST   | `warrantycreate/`  | Create warranty record          |
| GET    | `warranty-check/`  | Check warranty by serial number |
| GET    | `warranty-search/` | Search warranty records         |

---

## Messaging

| Method | Path                 | Description               |
| ------ | -------------------- | ------------------------- |
| POST   | `whatsapp_post/`     | Send WhatsApp message     |
| POST   | `whatsapp_webhooks/` | WhatsApp delivery webhook |
| POST   | `sms_webhooks/`      | SMS delivery webhook      |
| POST   | `rcs_post/`          | Send RCS message          |

---

## URL Management

| Method | Path                  | Description          |
| ------ | --------------------- | -------------------- |
| POST   | `generate/short-url/` | Generate a short URL |
| GET    | `shorturl/`           | Resolve short URL    |

---

## Cascade / Hierarchical QR

| Method   | Path               | Description                       |
| -------- | ------------------ | --------------------------------- |
| GET/POST | `parentqr/`        | Manage parent QR codes            |
| POST     | `child_qrs/`       | Create child QR codes             |
| POST     | `map_qrs/`         | Map parent-child QR relationships |
| POST     | `scanqrs/`         | Track cascade QR scan             |
| GET      | `labels_download/` | Download QR label batch           |
| GET/POST | `cascade-history/` | Cascade scan history              |

---

## Destinations / Markets

| Method   | Path                    | Description                   |
| -------- | ----------------------- | ----------------------------- |
| GET/POST | `destinations/`         | Destination market management |
| GET      | `destination/currency/` | Currency by destination       |

---

## Lead / CRM

| Method   | Path        | Description                |
| -------- | ----------- | -------------------------- |
| GET/POST | `userinfo/` | Create or list brand leads |

---

## Brand Trust Assessment

| Method | Path                     | Description               |
| ------ | ------------------------ | ------------------------- |
| GET    | `questions/`             | List assessment questions |
| POST   | `start/`                 | Start a brand assessment  |
| POST   | `submit/`                | Submit assessment answers |
| GET    | `assessment-report/`     | Get assessment report     |
| GET    | `brandtrust-pdf/`        | Generate brand trust PDF  |
| POST   | `send-brandtrust-email/` | Email brand trust report  |
| GET    | `brandindustry/`         | List industries           |

---

## Public / Marketing

| Method | Path             | Description             |
| ------ | ---------------- | ----------------------- |
| POST   | `contactus/`     | Contact form submission |
| POST   | `career_form/`   | Career application      |
| POST   | `schedule_demo/` | Schedule a demo         |
| POST   | `subscribe/`     | Newsletter subscription |
| POST   | `request_call/`  | Request a callback      |

---

## Admin / Tenant

| Method | Path             | Description                 |
| ------ | ---------------- | --------------------------- |
| POST   | `create-tenant/` | Create a new tenant (async) |
| GET    | `hello-view/`    | Health check                |

---

## API Documentation

| Path              | Description           |
| ----------------- | --------------------- |
| `/api/v1/schema/` | OpenAPI schema (JSON) |
| `/api/v1/doc/`    | Swagger UI            |
| `/api/v1/redoc/`  | ReDoc UI              |

---

## Authentication Schemes

### Token Auth

- Header: `Authorization: Token <token>`
- Tokens expire after ~24 hours (`TOKEN_EXPIRED_AFTER_SECONDS = 86900`)
- Expired tokens are auto-deleted and a new one is issued

### API Key Auth

- Header: `Authorization: Api-Key <key>` or custom header `HTTP_X_API_KEY`
- Two scopes: `F` (Factory/internal), `L` (Landing page)
- Validated against `BrandwiseAPIKey` model

---

## Rate Limits

| Scope              | Limit     |
| ------------------ | --------- |
| `user`             | 2000/hour |
| `anon`             | 200/hour  |
| `OTP`              | 40/hour   |
| `Tenant`           | 20/hour   |
| `product_activate` | 3000/hour |
| `qr_scans`         | 3000/hour |
| `feedback`         | 100/hour  |
| `warranty`         | 100/hour  |
| `brand`            | 100/day   |
| `shorturl`         | 50/day    |
| `authentic`        | 2/day     |

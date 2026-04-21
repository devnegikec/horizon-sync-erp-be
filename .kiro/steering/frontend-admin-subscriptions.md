---
inclusion: manual
---

# Frontend Admin Subscriptions & Billing Module - Integration Guide

Complete API reference for building the Admin Subscription and Billing UI. This module lets system admins view subscription status counts, identify expiring and overdue organizations, and inspect per-org billing details.

## Base URL & Auth

```
Core Service: http://localhost:8001/api/v1
Auth:         Authorization: Bearer {token}
```

All subscription admin endpoints require a valid Bearer token with `user_type = "system_admin"`. N
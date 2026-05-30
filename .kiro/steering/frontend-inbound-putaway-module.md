# Frontend — Inbound Receiving & Put-Away Module

## Overview

This document covers the complete **Inbound → Receiving Slip → Put-Away** workflow.
It is the authoritative integration guide for the frontend team.

Base URL: `http://localhost:9000/api/v1`
All endpoints require: `Authorization: Bearer {token}`

---

## Workflow at a Glance

```
1. POST /inbound/sessions                          → create session (status: open)
2. POST /inbound/sessions/{id}/scan  (×N)          → scan each QR code
3. GET  /inbound/sessions/{id}/summary             → optional: preview before ending
4. POST /inbound/sessions/{id}/end                 → close session → ReceivingSlip created (status: pending_review)
5. POST /inbound/receiving-slips/{id}/approve      → approve slip → PutAwayList auto-created (status: pending)
   OR
   POST /inbound/receiving-slips/{id}/reject       → reject with reason
6. GET  /put-away-lists                            → list put-away lists
7. GET  /put-away-lists/{id}                       → get list with bin assignments
8. POST /put-away-lists/{id}/items/{item_id}/complete  → mark item done (adds stock to bin)
   OR
   POST /put-away-lists/{id}/items/{item_id}/skip      → skip item with reason
```

Status transitions:

- Session: `open` → `closed`
- ReceivingSlip: `pending_review` → `pending_putaway` → `putaway_complete`
  `pending_review` → `rejected`
- PutAwayList: `pending` → `completed`
- PutAwayListItem: `pending` → `completed` | `skipped`

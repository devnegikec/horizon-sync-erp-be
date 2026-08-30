# WMS Outbound Pick — Explained in Plain English

> What we built in PR-01 → PR-14, and what happens step by step when something
> goes wrong during the outbound (picking) process.
>
> Audience: anyone who wants the "why" and "what happens when…" without reading code.

---

## 1. The 30-second version

When a sales order / SAP invoice arrives, the warehouse has to **pick the goods
off the shelves, put them on the right trolley/pallet, stage them at the right
door, and ship them** — while making sure:

1. The right item is picked, from the **right bin**, in the **right quantity**.
2. **Mistakes are caught immediately** (not discovered at the truck).
3. When something genuinely can't be completed, it is **recorded, explained,
   and escalated** — never silently ignored.
4. The **same action can't happen twice** (e.g. a double-tap on the scanner).
5. The **ERP (SAP) is told the final status**, reliably, even if SAP is down.
6. Every rule can be **turned on/off per customer** without changing code.

We built all of that as a chain of small, independent pieces (PR-01 → PR-14).

---

## 2. The outbound journey (happy path)

```
 SAP invoice
    │
    ▼
[1] Create pick list  ──▶  [2] Pick (scan bin → scan item → confirm qty)
    │                                    │
    ▼                                    ▼  (problems go to the exception queue)
[3] Complete            ◀────────  all lines done / exceptions approved
    │
    ▼
[4] Stage (assign lane → scan lane)
    │
    ▼
[5] Dispatch (gate check → truck)
    │
    ▼
[6] Tell SAP the status  (queue + retry + alert)
```

Each step is explained below in plain language, together with **what happens
when it goes wrong**.

---

## 3. Step-by-step: the happy path and the exceptions

### Step 1 — An order arrives

- SAP sends an invoice, or the office uploads a packing-slip PDF/CSV.
- The system creates a **pick list** (a "to-do list" of items + quantities) and
  figures out **which bin** to take each item from.

**Smart bin choice (PR-01):** every shelf/bin has a stock "health label":

| Label | Meaning | Can it be picked? |
|---|---|---|
| `available` | good stock | ✅ yes |
| `blocked` | on hold | ❌ skipped |
| `damaged` | broken/damaged | ❌ skipped |
| `hold` | held for review | ❌ skipped |
| `quality` | under QA | ❌ skipped |
| `reserved` | already promised | ❌ skipped |

The system only ever suggests **available** stock, oldest first (FIFO/FEFO).

**What goes wrong here (WF-001/002):** a malformed invoice or a line whose SKU
doesn't exist → the import is **rejected with a clear error** instead of
creating a half-broken pick list.

---

### Step 2 — The picker picks

The picker scans **the bin first, then the item**, then confirms quantity.

**a) Wrong bin → hard stop (PR-05, ALT-001)**
- If the rule "require bin scan" is ON, the scanned bin **must match** the bin
  the system assigned.
- Wrong bin → the scan is **rejected immediately**. The picker cannot proceed.
- If the rule is OFF (legacy customer), no bin check happens.

**b) Wrong SKU / wrong serial → hard stop (PR-06, PR-13 baseline)**
- The scanned SKU must be on the pick list. Wrong SKU → rejected.
- For serialized items, the scanned serial must:
  - belong to that SKU,
  - not already be **consumed**,
  - not be **blocked**.
  Otherwise → rejected with a clear message.

**c) Picking too much → blocked (PR-07, EX-021)**
- There's a tolerance setting ("over_pick_tolerance", default 0 = no
  over-picking). Scan more than allowed → blocked.

**d) Picking too little → short-pick (PR-07, EX-002 / ALT-004)**
- If "allow short pick" is ON and the shortfall is within the approval
  threshold, the line is allowed to finish short — and the shortfall is
  **recorded as an exception** automatically.
- If short-pick is OFF or above the threshold, it is **blocked** until a
  supervisor approves.

**e) Found something wrong (damage / expiry / wrong item in bin) (PR-03, PR-07)**
- The picker reports a **reason code** at scan time: `damaged`, `expired`,
  `wrong_item`, `bin_empty`, `insufficient_quantity`, `serial_missing`,
  `serial_consumed`, `other`.
- This creates an **exception** (see "The exception system" below).

**f) Double-tap / retry safety (PR-04, EX-017)**
- Every scan carries an **idempotency key**. If the same scan arrives twice
  (flaky network, double-tap), the system applies it **once** and returns the
  same result — the stock is never decremented twice.

**g) Stock movement is tracked (PR-08)**
- As items are picked, stock moves `available → picked → in-transit-to-stage`
  on a movement ledger, so you can always trace where stock went.

---

### Step 3 — Completing the pick

- The picker (or supervisor) hits **Complete**.
- The system checks every line:
  - Fully picked → fine.
  - Short within policy → records the exception and lets it complete.
  - Short not allowed / over threshold → **completion is blocked** until a
    supervisor resolves it (PR-07).
- A first scan already moved the list to `in_progress`; completing moves it to
  `completed` with a timestamp.

---

### Step 4 — Staging (PR-10)

- The picked goods go to a **staging lane** (a warehouse location typed
  "staging" — a dock door/lane).
- `stage-transfer` assigns the lane and moves picked stock to
  `in-transit-to-stage`.
- `stage-scan` validates the **scanned lane matches** the assigned lane:
  - **Wrong lane → hard stop (ALT-008).**
  - No lane assigned / lane unavailable → **exception** (EX-019/020).
- On success the pick list is stamped `staged_at`.

---

### Step 5 — Handling units (PR-11, optional)

- If "enable handling units" is ON, each pick line can be linked to a
  **trolley / carton / pallet** so you know what physical container the goods
  are in.
- The same handling unit **can't be used by two different lines** (duplicate
  rejected).

---

### Step 6 — Prioritization & aging (PR-12)

- Each pick list can carry `priority`, `dispatch_cutoff`, `wave`, `route`, and
  an optional per-task `sla_minutes`.
- Lists can be sorted by priority (higher first, then earlier cutoff, wave,
  route).
- **Aging alert (ALT-011):** if an open task sits longer than
  `aging_threshold_minutes` (default 120), it is flagged **"Aged"** so
  supervisors can react before the SLA blows.

#### A closer look at "aging" (ALT-011)

A common misconception is that aging means **"time-bound picking"** — i.e. a
hard deadline that forces or cancels the pick. **It is not.** Aging is a
*visibility / warning* feature:

| Question | Answer |
|---|---|
| What does it measure? | How long an **open** pick list (`draft` / `in_progress`) has been sitting since it was created. |
| What does it do? | Once the age crosses the threshold, the task is flagged **"Aged"** (an amber badge in the UI). |
| What does it *not* do? | It does **not** reorder tasks, block scanning, auto-cancel, or take any corrective action. It only *surfaces* the risk to supervisors. |

So it is **time awareness for supervisors**, not **time enforcement on
pickers**.

**How the flag is computed:**

```
age_minutes  = (now − created_at) in minutes        # created_at, falling back to pick_date
threshold    = sla_minutes (if set on the pick list)
               else aging_threshold_minutes         # org config, default 120
is_aging     = age_minutes >= threshold
```

- `get_list` resolves the org's `aging_threshold_minutes` once and annotates
  every pick list with `age_minutes` + `is_aging`.
- The frontend shows the amber "Aged" badge whenever `is_aging` is `true`.

**Configuration knobs (both numeric — there is no on/off switch today):**

| Key | Type | Default | Meaning |
|---|---|---|---|
| `pick.aging_threshold_minutes` | int | `120` | Org-wide age before a task is flagged |
| `sla_minutes` (per pick list) | int | `null` | Per-task override — if set, it wins over the org threshold |

> **Note:** there is currently **no boolean "enable/disable" flag** for aging.
> The feature is always computed and shown. To "turn it off" you would need to
> set an impractically large threshold — a real `enable_aging_alert` toggle has
> not been added (kept out per the original plan, which specified only the
> numeric threshold).

---

### Step 7 — Dispatch & telling SAP (PR-13)

- After gate verification, a **dispatch record** is created (existing flow).
- On pick completion and on dispatch, an **outbound sync message** is queued
  to tell SAP the status (WF-022).
- The queue delivers with **retry + exponential backoff**:
  - Success → message marked `sent`.
  - Transient failure → retry later.
  - **Retries exhausted → message marked `failed` and an in-app alert is
    raised** ("ERP sync failed", ALT-009).
- This means SAP being briefly down **never loses** the status update.

---

## 4. The exception system (the heart of "what happens when something goes wrong")

Built in **PR-03** and completed in **PR-07 / PR-09**.

**An exception is a structured record** of "this didn't go to plan":

| Field | Example |
|---|---|
| reason code | `damaged`, `bin_empty`, `insufficient_quantity`, … |
| severity | info / warning / error / critical |
| who reported it | the picker |
| affected quantity | 2 cases |
| status | open → approved / rejected / resolved / cancelled |
| audit trail | every decision, append-only |

**The lifecycle in plain words:**

1. **Raise** — picker hits an exception (damaged item, empty bin, short pick…).
   The system records it with a reason code and severity.
2. **Queue** — it appears in the **supervisor dashboard** (PR-09), filterable
   by severity/status.
3. **Approve / resolve** — a supervisor approves (e.g. "yes, allow the short
   pick") or resolves it with a note.
4. **Alert** — when resolved/approved, the reporter gets an **in-app
   notification** (`pick_exception`). Email is a documented extension point.
5. **Audit** — every step (capture, approve, reject, resolve) is written to an
   **append-only trail** that can never be edited or deleted (WF-023, NFR-005).

**Rules that make this safe:**

- A **duplicate exception** (same item + same reason still open) is rejected —
  no double-counting.
- Reason codes come from a **configurable master list** per organization.
- A line with a **short-pick that needs approval** blocks completion until
  approved.

---

## 5. Worked example #1 — "The bin is empty"

1. Picker scans the assigned bin, then the item. There are 0 units.
2. Picker reports reason `bin_empty`.
3. The system **records an exception** (severity warning, reason `bin_empty`).
4. If another bin has stock, the system already suggested it (multi-bin split
   from PR-01/bin resolution) — otherwise the line is short.
5. The line is short → short-pick policy applies: within threshold → complete
   with an `insufficient_quantity` exception; over threshold → **blocked until
   a supervisor approves**.
6. Supervisor sees it in the queue, approves, and the pick list can complete.

---

## 6. Worked example #2 — "SAP goes down"

1. Picker completes the pick list.
2. The system writes `pick_list` status to the **ERP sync queue**
   (`pending`).
3. Delivery tries and fails (SAP down) → `attempt_count` +1, schedules a retry
   with backoff.
4. SAP is still down after the retry budget (`erp_sync_max_retries`, default 3)
   → message marked `failed`, and an **in-app alert** is raised
   (`erp_sync_failed`).
5. A human (or a later manual flush) retries with the "Flush retries" action —
   the message is **never silently lost**.

---

## 7. What each PR added (plain-English cheat sheet)

| PR | Feature | Plain-English |
|---|---|---|
| PR-01 | Inventory status | Shelves have health labels; only "available" gets picked. |
| PR-02 | Config layer | Every rule is a switch/tuning knob per customer. |
| PR-03 | Exceptions + audit | "Something went wrong" is recorded, explained, and can't be tampered with. |
| PR-04 | Idempotency | Double-taps and retries can't double-move stock. |
| PR-05 | Wrong-bin hard stop | Scan the wrong bin and the system stops you. |
| PR-06 | Serial validation | Serials must match the SKU and not be used/blocked. |
| PR-07 | Short/over pick + damage | Over-pick blocked; short-pick becomes an exception; damage captured. |
| PR-08 | Movement states | Stock moves available → picked → in-transit. |
| PR-09 | Supervisor queue | Supervisors see and resolve/approve exceptions; reporters get alerted. |
| PR-10 | Staging | Assign a lane, scan it; wrong lane stops you. |
| PR-11 | Handling units | Link lines to trolley/carton/pallet; no double-booking. |
| PR-12 | Priority + aging | Sort by urgency; flag tasks that are getting old. |
| PR-13 | ERP sync queue | Tell SAP reliably with retry; alert if it keeps failing. |
| PR-14 | Accept + sessions | Accept records start time; lockout after bad logins; idle timeout. |

---

## 8. One-line answer to "what happens when an exception occurs?"

> The picker can't (or shouldn't) complete the step → the system **blocks the
> dangerous action immediately** → the picker **records a reason code** → an
> **exception** is created and shown in the **supervisor queue** → the
> supervisor **approves/resolves** → the reporter is **notified** → everything
> is written to an **immutable audit trail** → and, if it affects SAP, the
> **sync queue retries and alerts** so nothing is lost.

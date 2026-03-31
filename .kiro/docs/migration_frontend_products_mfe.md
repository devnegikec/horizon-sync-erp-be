### **Technical Specification: Products-MFE (React + TypeScript)**
**Document ID:** B — React + TypeScript Frontend
**Project:** Horizon Sync ERP Migration
**Status:** Draft / Specification

---

## **1. Purpose and Goals**
The primary objective is to replace the legacy monolith UI responsible for QR block generation with a modern, scalable **Micro-Frontend (MFE)**.
* **Modernization:** Transition from the monolith to a React + TypeScript architecture.
* **Functional Scope:** Provide forms for block creation, real-time progress tracking, data validation, and asset management (Excel/QR downloads).
* **Communication:** Implement robust state management and asynchronous communication via Polling or WebSockets.

---

## **2. Architecture & Components**

### **Core UI Components**
| Component | Responsibility |
| :--- | :--- |
| **`BlockCreateForm.tsx`** | Form for selecting products, quantity, and QR configurations. |
| **`BlockStatusPanel.tsx`** | Displays real-time progress, status badges, and download links. |
| **`BlockItemsTable.tsx`** | A paginated data grid for viewing generated `ProductItem` records. |
| **`NotificationSystem`** | Toast-based feedback for success, warnings, and API errors. |

### **Services**
* **`api.ts`**: A central Axios/Fetch client configured with:
    * JWT Authorization headers.
    * Base URL configuration via environment variables.
    * Global error interceptors for 401 (Auth) and 422 (Credits) handling.

---

## **3. Technical Contracts**

### **API Integration**
* **Create Block:** `POST /api/v1/blocks` ➔ Returns `{ id, status_url, task_id }`.
* **Check Status:** `GET /api/v1/blocks/{id}` ➔ Returns status, progress (0-100), and `download_url`.
* **Fetch Data:** `GET /api/v1/blocks/{id}/items` ➔ Paginated list of generated items.

### **Data Models (TypeScript)**
```typescript
export type QRType = 'S' | 'C' | 'B' | 'O' | 'SC' | 'D';

export interface Block {
  id: number;
  product_id: number;
  quantity: number;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress?: number;
  download_url?: string | null;
  created_at: string;
}

export interface ProductItem {
  serial_number: string;
  secret_code?: string | null;
  short_url?: string | null;
  qr_image_uri?: string | null;
}
```

---

## **4. UX Flows & Logic**

### **Generation Workflow**
1.  **Form Input:** User selects product and quantity. System displays "Remaining Credits" badge.
2.  **Submission:** On `201 Success`, UI redirects to the **BlockStatusPanel**.
3.  **Polling Strategy:** * Start at **1s** intervals.
    * Apply **exponential backoff** (e.g., 1s → 3s → 10s) to reduce server load for large batches.
4.  **Completion:** Once `status === 'completed'`, enable the "Download Excel" button and the "View Items" table.

### **Error Handling**
* **422 Unprocessable Entity:** Trigger "Insufficient Credits" modal with a CTA to contact support.
* **409 Conflict:** Block is locked/generating; maintain polling state.
* **Network Failure:** Automatic retry with exponential backoff and a "Connection Lost" toast.

---

## **5. Deployment & Testing**

* **Micro-Frontend Strategy:** Build as a standalone static bundle deployed to a CDN (S3/CloudFront).
* **Security:** JWTs managed via memory or `httpOnly` cookies; CORS enforced on FastAPI.
* **Testing Suite:**
    * **Unit:** Jest + RTL for component rendering logic.
    * **Integration:** MSW (Mock Service Worker) to simulate API interactions.
    * **E2E:** Cypress/Playwright to validate the full "Create-to-Download" flow.

---

## **6. Developer Roadmap**

* [ ] **Phase 1:** Scaffold React app (TS, Tailwind, Router, Axios).
* [ ] **Phase 2:** Develop `BlockCreateForm` with credit-check validation.
* [ ] **Phase 3:** Implement `BlockStatusPanel` with backoff polling logic.
* [ ] **Phase 4:** Develop `BlockItemsTable` with pagination and search.
* [ ] **Phase 5:** End-to-end integration with FastAPI (Staging).
* [ ] **Phase 6:** Production rollout via Feature Flag.

---

## **7. Appendix: Recommended Cutover**
1.  **Side-by-Side:** Deploy the MFE alongside the monolith. Use a feature flag to route a subset of users to the new UI.
2.  **Delegation:** Have the monolith's legacy API act as a proxy to the new FastAPI service until the frontend migration is 100% complete.
3.  **Decommission:** Monitor for 14 days post-100% rollout, then strip legacy Django generation tasks.

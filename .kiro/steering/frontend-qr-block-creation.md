# Frontend: QR Block Creation — Implementation Guide

## Overview

This steering file covers the end-to-end frontend implementation for creating digitally signed QR blocks. It focuses specifically on the block creation workflow, from brand setup through block generation and status tracking.

The full workflow is:

1. Create a Brand (auto-generates ECDSA P-256 key pair)
2. Create a QR Product linked to that Brand
3. Create a QR Block (triggers signed QR code generation)
4. Poll block status until `completed` or `failed`
5. Download the generated Excel file from `download_url`

---

## Backend Spec Reference

- Requirements: `.kiro/specs/key-generation-block-creation/requirements.md`
- Design: `.kiro/specs/key-generation-block-creation/design.md`
- Tasks: `.kiro/specs/key-generation-block-creation/tasks.md`

---

## API Endpoints

### Base URL

```
http://localhost:8001/api/v1
```

### Authentication

All endpoints require Bearer token except `/qr-products/authenticate`:

```
Authorization: Bearer {token}
```

### Brand Endpoints

| Method | Path           | Permission     | Description                         |
| ------ | -------------- | -------------- | ----------------------------------- |
| POST   | `/brands`      | `brand.create` | Create brand + auto ECDSA key pair  |
| GET    | `/brands`      | `brand.read`   | List brands (paginated, searchable) |
| GET    | `/brands/{id}` | `brand.read`   | Get single brand                    |
| PATCH  | `/brands/{id}` | `brand.update` | Update name/short_code only         |

> No DELETE endpoint. Brands persist indefinitely.

### QR Block Endpoints

| Method | Path                                   | Permission          | Description                    |
| ------ | -------------------------------------- | ------------------- | ------------------------------ |
| POST   | `/qr-products/{id}/blocks`             | `qr_product.create` | Create block (signed if brand) |
| GET    | `/qr-products/{id}/blocks`             | `qr_product.read`   | List blocks for a product      |
| GET    | `/qr-products/blocks/{block_id}`       | `qr_product.read`   | Get block detail + status      |
| GET    | `/qr-products/blocks/{block_id}/items` | `qr_product.read`   | List generated ProductItems    |
| POST   | `/qr-products/authenticate`            | public (no auth)    | Verify QR signature            |

---

## TypeScript Types

```typescript
// types/brand.types.ts

export interface BrandCreate {
  name: string; // max 256 chars
  short_code: string; // max 256 chars — used in QR URLs
}

export interface BrandUpdate {
  name?: string;
  short_code?: string;
  // NEVER include public_key or private_key_encrypted — backend returns 422
}

export interface Brand {
  id: string;
  organization_id: string;
  name: string;
  short_code: string;
  public_key: string; // uncompressed X9.62 hex, starts with "04", exactly 130 chars
  created_by: string | null;
  created_at: string;
  updated_at: string;
  // private_key_encrypted is NEVER returned by the API
}

export interface BrandListResponse {
  brands: Brand[];
  pagination: Pagination;
}
```

```typescript
// types/qrBlock.types.ts

export type QRType = "D" | "S" | "B" | "O" | "SC";
export type SerialNumberType = "R6DAN" | "R4DAN" | "S8DN" | "S10DN";
export type BlockStatus = "pending" | "in_progress" | "completed" | "failed";

export interface QRBlockCreate {
  batch: string; // max 50 chars, required
  quantity: number; // 1–10000, required
  qr_type?: QRType; // defaults to "D" if omitted
  serial_prefix?: string;
  sr_number_type?: SerialNumberType;
  qr_image?: boolean;
  manufacture_date?: string; // ISO date
  expiry_date?: string; // ISO date
}

export interface QRBlock {
  id: string;
  product_id: string;
  organization_id: string;
  batch: string;
  quantity: number;
  qr_type: QRType | null;
  status: BlockStatus;
  task_id: string | null;
  download_url: string | null; // only set when status === "completed"
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface QRBlockListResponse {
  blocks: QRBlock[];
  pagination: Pagination;
}

export interface ProductItem {
  id: string;
  product_id: string;
  block_id: string;
  serial_number: string;
  qr_active: boolean;
  scan_count: number;
  last_scanned_at: string | null;
  secret_code: string | null; // only populated for SC (SecureCode) type
  created_at: string;
}

export interface ProductItemListResponse {
  items: ProductItem[];
  pagination: Pagination;
}

export interface AuthenticateRequest {
  serial_number: string;
  nonce: string; // timestamp string from QR URL path
  cipher: string; // base64 signature from ?c= query param
}

export interface AuthenticateResponse {
  message: string;
  authentic: boolean;
  product_name: string | null;
  brand_name: string | null;
  gtin: string | null;
  serial_number: string | null;
}

export interface Pagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}
```

---

## QR Type Reference

| Code | Name       | Behavior                                                      |
| ---- | ---------- | ------------------------------------------------------------- |
| D    | Dynamic    | Unique URL per item, standard ECDSA verification              |
| S    | Static     | All items share the same serial number, only timestamp varies |
| B    | Dual       | Two QR codes per item (covert + overt) with separate URLs     |
| O    | OneTime    | `qr_active` set to `false` after first successful scan        |
| SC   | SecureCode | Each item has a 12-char `secret_code` stored in the record    |

## Serial Number Type Reference

| Code  | Format                          |
| ----- | ------------------------------- |
| R6DAN | 6-char random alphanumeric      |
| R4DAN | 4-char random alphanumeric      |
| S8DN  | Zero-padded 8-digit sequential  |
| S10DN | Zero-padded 10-digit sequential |

---

## QR URL Format

Generated QR codes follow this pattern:

```
https://{org_short_code}.{domain}/g/{gtin}/s/{serial_number}/{timestamp}?c={base64_signature}
```

When parsing a scanned QR URL to call `/authenticate`:

- `serial_number` → path segment after `/s/`
- `nonce` → timestamp path segment after serial_number
- `cipher` → `c` query parameter (base64 ECDSA signature)

---

## Credit System

Before a block is created, the backend checks `QRCreditBalance.balance_credits >= quantity`. Credits are only deducted **after** successful generation. If generation fails, credits remain unchanged.

Key behaviors to handle in the UI:

- `422` with `"No credit balance configured"` → org has no credit record; contact admin
- `422` with `"Insufficient credits: available=X, required=Y"` → show remaining balance and direct user to top up
- Credits are deducted atomically with a ledger entry — no partial deductions

---

## API Service Implementation

```typescript
// services/brandService.ts

import axios from "axios";
import type {
  Brand,
  BrandCreate,
  BrandUpdate,
  BrandListResponse,
} from "../types/brand.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class BrandService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async create(data: BrandCreate): Promise<Brand> {
    const response = await axios.post(`${API_BASE_URL}/api/v1/brands`, data, {
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async list(params?: {
    page?: number;
    page_size?: number;
    search?: string;
  }): Promise<BrandListResponse> {
    const response = await axios.get(`${API_BASE_URL}/api/v1/brands`, {
      headers: this.getHeaders(),
      params,
    });
    return response.data;
  }

  async getById(id: string): Promise<Brand> {
    const response = await axios.get(`${API_BASE_URL}/api/v1/brands/${id}`, {
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async update(id: string, data: BrandUpdate): Promise<Brand> {
    // Strip any key fields — backend returns 422 if they're included
    const { name, short_code } = data;
    const response = await axios.patch(
      `${API_BASE_URL}/api/v1/brands/${id}`,
      { name, short_code },
      { headers: this.getHeaders() },
    );
    return response.data;
  }
}

export const brandService = new BrandService();
```

```typescript
// services/qrBlockService.ts

import axios from "axios";
import type {
  QRBlock,
  QRBlockCreate,
  QRBlockListResponse,
  ProductItemListResponse,
  AuthenticateRequest,
  AuthenticateResponse,
} from "../types/qrBlock.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class QRBlockService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async createBlock(productId: string, data: QRBlockCreate): Promise<QRBlock> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/qr-products/${productId}/blocks`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async listBlocks(
    productId: string,
    params?: { page?: number; page_size?: number; status?: BlockStatus },
  ): Promise<QRBlockListResponse> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/qr-products/${productId}/blocks`,
      { headers: this.getHeaders(), params },
    );
    return response.data;
  }

  async getBlock(blockId: string): Promise<QRBlock> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/qr-products/blocks/${blockId}`,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async getBlockItems(
    blockId: string,
    params?: { page?: number; page_size?: number },
  ): Promise<ProductItemListResponse> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/qr-products/blocks/${blockId}/items`,
      { headers: this.getHeaders(), params },
    );
    return response.data;
  }

  async authenticate(data: AuthenticateRequest): Promise<AuthenticateResponse> {
    // Public endpoint — no auth header needed
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/qr-products/authenticate`,
      data,
    );
    return response.data;
  }
}

export const qrBlockService = new QRBlockService();
```

---

## React Hooks

```typescript
// hooks/useCreateBrand.ts

import { useState } from "react";
import { brandService } from "../services/brandService";
import type { Brand, BrandCreate } from "../types/brand.types";

export const useCreateBrand = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createBrand = async (data: BrandCreate): Promise<Brand> => {
    setLoading(true);
    setError(null);
    try {
      return await brandService.create(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create brand");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createBrand, loading, error };
};
```

```typescript
// hooks/useCreateBlock.ts

import { useState } from "react";
import { qrBlockService } from "../services/qrBlockService";
import type { QRBlock, QRBlockCreate } from "../types/qrBlock.types";

export const useCreateBlock = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createBlock = async (
    productId: string,
    data: QRBlockCreate,
  ): Promise<QRBlock> => {
    setLoading(true);
    setError(null);
    try {
      return await qrBlockService.createBlock(productId, data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to create block");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createBlock, loading, error };
};
```

```typescript
// hooks/useBlockStatus.ts — polls until terminal status

import { useState, useEffect, useRef } from "react";
import { qrBlockService } from "../services/qrBlockService";
import type { QRBlock, BlockStatus } from "../types/qrBlock.types";

const TERMINAL_STATUSES: BlockStatus[] = ["completed", "failed"];
const POLL_INTERVAL_MS = 3000;

export const useBlockStatus = (blockId: string | null) => {
  const [block, setBlock] = useState<QRBlock | null>(null);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const fetchBlock = async () => {
    if (!blockId) return;
    try {
      const data = await qrBlockService.getBlock(blockId);
      setBlock(data);
      if (TERMINAL_STATUSES.includes(data.status)) stopPolling();
    } catch {
      stopPolling();
    }
  };

  useEffect(() => {
    if (!blockId) return;
    setLoading(true);
    fetchBlock().finally(() => setLoading(false));
    intervalRef.current = setInterval(fetchBlock, POLL_INTERVAL_MS);
    return stopPolling;
  }, [blockId]);

  return { block, loading };
};
```

---

## Component Examples

### BrandForm

```typescript
// components/brands/BrandForm.tsx

import React, { useState } from "react";
import { useCreateBrand } from "../../hooks/useCreateBrand";
import type { Brand } from "../../types/brand.types";

export const BrandForm: React.FC<{ onSuccess?: (brand: Brand) => void }> = ({ onSuccess }) => {
  const { createBrand, loading, error } = useCreateBrand();
  const [name, setName] = useState("");
  const [shortCode, setShortCode] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const brand = await createBrand({ name, short_code: shortCode });
      onSuccess?.(brand);
    } catch {}
  };

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Brand Name *</label>
        <input type="text" value={name} onChange={(e) => setName(e.target.value)} maxLength={256} required />
      </div>
      <div className="form-group">
        <label>Short Code *</label>
        <input type="text" value={shortCode} onChange={(e) => setShortCode(e.target.value)} maxLength={256} required />
        <small>Used in QR URLs: https://&#123;short_code&#125;.domain/...</small>
      </div>
      {error && <div className="error-message">{error}</div>}
      <button type="submit" disabled={loading}>
        {loading ? "Creating..." : "Create Brand"}
      </button>
      <p className="hint">An ECDSA P-256 key pair will be auto-generated.</p>
    </form>
  );
};
```

### BlockCreateForm with inline status tracking

```typescript
// components/blocks/BlockCreateForm.tsx

import React, { useState } from "react";
import { useCreateBlock } from "../../hooks/useCreateBlock";
import { useBlockStatus } from "../../hooks/useBlockStatus";
import { BlockStatusBadge } from "./BlockStatusBadge";
import type { QRType, SerialNumberType } from "../../types/qrBlock.types";

const QR_TYPE_LABELS: Record<QRType, string> = {
  D: "Dynamic — unique URL per item",
  S: "Static — same serial for all items",
  B: "Dual — covert + overt QR per item",
  O: "OneTime — deactivates after first scan",
  SC: "SecureCode — 12-char secret per item",
};

export const BlockCreateForm: React.FC<{
  productId: string;
  onCreated?: (blockId: string) => void;
}> = ({ productId, onCreated }) => {
  const { createBlock, loading, error } = useCreateBlock();
  const [createdBlockId, setCreatedBlockId] = useState<string | null>(null);
  const { block } = useBlockStatus(createdBlockId);

  const [batch, setBatch] = useState("");
  const [quantity, setQuantity] = useState(100);
  const [qrType, setQrType] = useState<QRType>("D");
  const [srNumberType, setSrNumberType] = useState<SerialNumberType>("R6DAN");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = await createBlock(productId, {
        batch,
        quantity,
        qr_type: qrType,
        sr_number_type: srNumberType,
      });
      setCreatedBlockId(result.id);
      onCreated?.(result.id);
    } catch {}
  };

  // After creation, show live status tracker
  if (createdBlockId && block) {
    return (
      <div className="block-status-tracker">
        <h3>Block Generation Status</h3>
        <p>Block: {createdBlockId}</p>
        <BlockStatusBadge status={block.status} />
        {block.status === "in_progress" && <p>Generating {block.quantity} QR codes...</p>}
        {block.status === "completed" && block.download_url && (
          <a href={block.download_url} target="_blank" rel="noreferrer">
            Download Excel
          </a>
        )}
        {block.status === "failed" && (
          <p className="error-message">Generation failed. Credits were not deducted.</p>
        )}
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Batch Name * (max 50 chars)</label>
        <input type="text" value={batch} onChange={(e) => setBatch(e.target.value)} maxLength={50} required />
      </div>

      <div className="form-group">
        <label>Quantity * (1–10,000)</label>
        <input
          type="number"
          value={quantity}
          onChange={(e) => setQuantity(Number(e.target.value))}
          min={1}
          max={10000}
          required
        />
      </div>

      <div className="form-group">
        <label>QR Type</label>
        <select value={qrType} onChange={(e) => setQrType(e.target.value as QRType)}>
          {(Object.keys(QR_TYPE_LABELS) as QRType[]).map((type) => (
            <option key={type} value={type}>
              {type} — {QR_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Serial Number Type</label>
        <select value={srNumberType} onChange={(e) => setSrNumberType(e.target.value as SerialNumberType)}>
          <option value="R6DAN">R6DAN — 6-char random alphanumeric</option>
          <option value="R4DAN">R4DAN — 4-char random alphanumeric</option>
          <option value="S8DN">S8DN — 8-digit sequential</option>
          <option value="S10DN">S10DN — 10-digit sequential</option>
        </select>
      </div>

      {error && <div className="error-message">{error}</div>}

      <button type="submit" disabled={loading}>
        {loading ? "Submitting..." : "Generate QR Block"}
      </button>
    </form>
  );
};
```

### BlockStatusBadge

```typescript
// components/blocks/BlockStatusBadge.tsx

import React from "react";
import type { BlockStatus } from "../../types/qrBlock.types";

const STATUS_CONFIG: Record<BlockStatus, { label: string; className: string }> = {
  pending:     { label: "Pending",       className: "status-pending" },
  in_progress: { label: "Generating...", className: "status-in-progress" },
  completed:   { label: "Completed",     className: "status-completed" },
  failed:      { label: "Failed",        className: "status-failed" },
};

export const BlockStatusBadge: React.FC<{ status: BlockStatus }> = ({ status }) => {
  const config = STATUS_CONFIG[status];
  return <span className={`status-badge ${config.className}`}>{config.label}</span>;
};
```

### PublicKeyDisplay (copyable)

```typescript
// components/brands/PublicKeyDisplay.tsx

import React, { useState } from "react";

export const PublicKeyDisplay: React.FC<{ publicKey: string }> = ({ publicKey }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(publicKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="public-key-display">
      <label>Public Key (ECDSA P-256)</label>
      <div className="key-row">
        <code className="key-value">{publicKey}</code>
        <button type="button" onClick={handleCopy}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <small>Uncompressed X9.62 hex — starts with "04", 130 characters</small>
    </div>
  );
};
```

---

## Authentication Flow (Public Endpoint)

The `/qr-products/authenticate` endpoint requires no auth token — it's called by consumer-facing scanner pages.

```typescript
// utils/qrAuthentication.ts

import axios from "axios";
import type {
  AuthenticateRequest,
  AuthenticateResponse,
} from "../types/qrBlock.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

// Parse a scanned QR URL into authenticate request params
export const parseQRUrl = (url: string): AuthenticateRequest => {
  const urlObj = new URL(url);
  const parts = urlObj.pathname.split("/");
  // Path: /g/{gtin}/s/{serial}/{timestamp}
  const sIndex = parts.indexOf("s");
  return {
    serial_number: parts[sIndex + 1],
    nonce: parts[sIndex + 2],
    cipher: urlObj.searchParams.get("c") || "",
  };
};

export const authenticateQR = async (
  qrUrl: string,
): Promise<AuthenticateResponse> => {
  const payload = parseQRUrl(qrUrl);
  const response = await axios.post(
    `${API_BASE_URL}/api/v1/qr-products/authenticate`,
    payload,
  );
  return response.data;
};
```

---

## Error Handling Reference

| HTTP | Scenario                                               | User-Facing Message                                 |
| ---- | ------------------------------------------------------ | --------------------------------------------------- |
| 403  | Missing `brand.create` / `brand.update` permission     | "You don't have permission to perform this action"  |
| 404  | Brand not found or belongs to another org              | "Brand not found"                                   |
| 409  | Duplicate `short_code` within org                      | "A brand with this short code already exists"       |
| 422  | PATCH includes `public_key` or `private_key_encrypted` | "Key fields cannot be updated"                      |
| 422  | QRProduct PATCH includes `brand_id`                    | "Brand cannot be changed after creation"            |
| 422  | No credit balance record for org                       | "No credit balance configured — contact your admin" |
| 422  | Insufficient QR credits                                | "Insufficient credits: available=X, required=Y"     |
| 422  | Block quantity out of range (0 or >10,000)             | "Quantity must be between 1 and 10,000"             |
| 400  | QR authenticate — serial not found                     | "Serial number not found"                           |
| 400  | QR authenticate — product not activated                | "Product has not been activated"                    |
| 400  | QR authenticate — signature invalid                    | "Authentication Failed"                             |

---

## Critical UX Rules

1. **Never show a key input on brand creation** — only `name` and `short_code`. The ECDSA key pair is auto-generated server-side.
2. **Public key is read-only** — display it in a copyable field. It's always a 130-char hex string starting with `"04"`.
3. **No delete button for brands** — the API has no DELETE endpoint. Don't render one.
4. **Block generation takes time** — always use `useBlockStatus` polling after creation. Never assume the block is ready immediately.
5. **Download URL only appears on `completed`** — gate the download button on `block.status === "completed" && block.download_url`.
6. **Credits are deducted only on success** — if status is `"failed"`, credits were NOT deducted. Inform the user they can retry.
7. **`brand_id` is immutable on QRProduct** — once set at creation, it cannot be changed. Don't show a brand selector on the edit form.
8. **Always show QR type descriptions** — never show just the code (D, S, B, O, SC). Always pair with the human-readable label.
9. **Insufficient credits** — parse the `detail` field from the 422 response to show available vs required credits. Direct the user to top up.

---

## Environment Variables

```env
REACT_APP_API_URL=http://localhost:8001
```

## Support & Resources

- Swagger UI: http://localhost:8001/docs
- Backend logs: `docker compose logs core-service`
- Brand endpoints: `core-service/app/api/v1/endpoints/brands.py`
- Block generation: `core-service/app/services/qr_product_service.py`
- Key service: `core-service/app/services/key_service.py`
- Credit service: `core-service/app/services/credit_service.py`

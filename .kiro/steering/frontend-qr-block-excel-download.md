---
inclusion: always
---

# Frontend — QR Block Creation & Excel Download

## Overview

This guide covers the `products-mfe` UI for creating a QR block (batch of unique QR codes),
polling for generation progress, and downloading the resulting Excel file. It maps to the
FastAPI Product & QR Service.

---

## Module Structure

```
src/features/blocks/
├── components/
│   ├── BlockCreateForm.tsx       # Form to submit a new block
│   ├── BlockList.tsx             # Paginated list of blocks per product
│   ├── BlockStatusBadge.tsx      # pending / in_progress / completed / failed
│   ├── BlockProgressPoller.tsx   # Polls status until completed/failed
│   └── BlockDownloadButton.tsx   # Fetches signed URL and triggers download
├── hooks/
│   ├── useCreateBlock.ts         # POST /blocks
│   ├── useBlocks.ts              # GET /blocks?product_id=
│   ├── useBlock.ts               # GET /blocks/{id}
│   ├── useBlockDownload.ts       # GET /blocks/{id}/download
│   └── useBlockPoller.ts         # Polls useBlock until terminal status
├── services/
│   └── blockService.ts           # Axios service class
├── types/
│   └── block.types.ts            # TypeScript interfaces
└── utils/
    └── serialHelpers.ts          # Serial number preview helpers
```

---

## TypeScript Types

```typescript
// types/block.types.ts

export type QRType = "D" | "S" | "B" | "O" | "SC";
export type SerialNumberType = "R6DAN" | "R4DAN" | "S8DN" | "S10DN";
export type BlockStatus = "pending" | "in_progress" | "completed" | "failed";

export interface BlockCreate {
  product_id: string;
  batch: string;
  quantity: number;
  qr_type: QRType;
  serial_prefix?: string | null;
  serial_number_type?: SerialNumberType | null;
  include_qr_image: boolean;
}

export interface Block {
  id: string;
  tenant_id: string;
  product_id: string;
  batch: string;
  quantity: number;
  qr_type: QRType;
  serial_prefix: string | null;
  serial_number_type: SerialNumberType | null;
  status: BlockStatus;
  include_qr_image: boolean;
  download_url: string | null;
  task_id: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface BlockListResponse {
  items: Block[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface BlockDownloadResponse {
  signed_url: string;
  expires_at: string;
}
```

---

## Service Class

```typescript
// services/blockService.ts

import axios from "axios";
import type { BlockCreate, Block, BlockListResponse, BlockDownloadResponse } from "../types/block.types";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8001";

class BlockService {
  private headers() {
    const token = /* get from auth context */;
    return { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
  }

  async create(data: BlockCreate): Promise<Block> {
    const res = await axios.post(`${API_BASE}/api/v1/blocks`, data, { headers: this.headers() });
    return res.data;
  }

  async list(params: { product_id: string; page?: number; page_size?: number; status?: BlockStatus }): Promise<BlockListResponse> {
    const res = await axios.get(`${API_BASE}/api/v1/blocks`, { headers: this.headers(), params });
    return res.data;
  }

  async getById(id: string): Promise<Block> {
    const res = await axios.get(`${API_BASE}/api/v1/blocks/${id}`, { headers: this.headers() });
    return res.data;
  }

  async getDownloadUrl(id: string): Promise<BlockDownloadResponse> {
    const res = await axios.get(`${API_BASE}/api/v1/blocks/${id}/download`, { headers: this.headers() });
    return res.data;
  }
}

export const blockService = new BlockService();
```

---

## Hooks

### useCreateBlock

```typescript
// hooks/useCreateBlock.ts

import { useState } from "react";
import { blockService } from "../services/blockService";
import type { BlockCreate, Block } from "../types/block.types";

export const useCreateBlock = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createBlock = async (data: BlockCreate): Promise<Block> => {
    setLoading(true);
    setError(null);
    try {
      return await blockService.create(data);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to create block";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createBlock, loading, error };
};
```

### useBlockPoller

Polls every 3 seconds until status is `completed` or `failed`, max 20 attempts.

```typescript
// hooks/useBlockPoller.ts

import { useState, useEffect, useRef } from "react";
import { blockService } from "../services/blockService";
import type { Block, BlockStatus } from "../types/block.types";

const TERMINAL: BlockStatus[] = ["completed", "failed"];
const POLL_INTERVAL_MS = 3000;
const MAX_ATTEMPTS = 20;

export const useBlockPoller = (blockId: string | null) => {
  const [block, setBlock] = useState<Block | null>(null);
  const [attempts, setAttempts] = useState(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!blockId) return;

    const poll = async () => {
      try {
        const data = await blockService.getById(blockId);
        setBlock(data);
        setAttempts((a) => a + 1);

        if (!TERMINAL.includes(data.status) && attempts < MAX_ATTEMPTS) {
          timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch {
        // silently retry
        timerRef.current = setTimeout(poll, POLL_INTERVAL_MS);
      }
    };

    poll();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [blockId]);

  const timedOut = attempts >= MAX_ATTEMPTS && block?.status !== "completed";
  return { block, timedOut };
};
```

### useBlockDownload

```typescript
// hooks/useBlockDownload.ts

import { useState } from "react";
import { blockService } from "../services/blockService";

export const useBlockDownload = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const download = async (blockId: string, filename?: string) => {
    setLoading(true);
    setError(null);
    try {
      const { signed_url } = await blockService.getDownloadUrl(blockId);
      // Trigger browser download
      const a = document.createElement("a");
      a.href = signed_url;
      a.download = filename || `qr_block_${blockId}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Download failed");
    } finally {
      setLoading(false);
    }
  };

  return { download, loading, error };
};
```

---

## Components

### BlockCreateForm

```typescript
// components/BlockCreateForm.tsx

import React, { useState } from "react";
import { useCreateBlock } from "../hooks/useCreateBlock";
import { useBlockPoller } from "../hooks/useBlockPoller";
import { BlockDownloadButton } from "./BlockDownloadButton";
import type { QRType, SerialNumberType } from "../types/block.types";

interface Props {
  productId: string;
  onCreated?: (blockId: string) => void;
}

export const BlockCreateForm: React.FC<Props> = ({ productId, onCreated }) => {
  const { createBlock, loading, error } = useCreateBlock();

  const [batch, setBatch] = useState("");
  const [quantity, setQuantity] = useState(100);
  const [qrType, setQrType] = useState<QRType>("D");
  const [serialPrefix, setSerialPrefix] = useState("");
  const [serialType, setSerialType] = useState<SerialNumberType>("S8DN");
  const [includeQrImage, setIncludeQrImage] = useState(false);
  const [createdBlockId, setCreatedBlockId] = useState<string | null>(null);

  const { block, timedOut } = useBlockPoller(createdBlockId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const result = await createBlock({
        product_id: productId,
        batch,
        quantity,
        qr_type: qrType,
        serial_prefix: serialPrefix || null,
        serial_number_type: serialType,
        include_qr_image: includeQrImage,
      });
      setCreatedBlockId(result.id);
      onCreated?.(result.id);
    } catch {
      // error shown via hook
    }
  };

  return (
    <div className="block-create-form">
      <h2>Generate QR Block</h2>

      {!createdBlockId ? (
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Batch Name *</label>
            <input
              value={batch}
              onChange={(e) => setBatch(e.target.value)}
              placeholder="e.g. BATCH-2025-01"
              maxLength={50}
              required
            />
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Quantity *</label>
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
              <label>QR Type *</label>
              <select value={qrType} onChange={(e) => setQrType(e.target.value as QRType)}>
                <option value="D">Dynamic — unique URL per item</option>
                <option value="S">Static — same serial per batch</option>
                <option value="B">Dual — covert + overt QR pair</option>
                <option value="O">One-Time — deactivates after first scan</option>
                <option value="SC">Secure Code — QR + 12-char secret</option>
              </select>
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label>Serial Number Type</label>
              <select value={serialType} onChange={(e) => setSerialType(e.target.value as SerialNumberType)}>
                <option value="S8DN">Sequential 8-digit (S8DN)</option>
                <option value="S10DN">Sequential 10-digit (S10DN)</option>
                <option value="R6DAN">Random 6-char alphanumeric (R6DAN)</option>
                <option value="R4DAN">Random 4-char alphanumeric (R4DAN)</option>
              </select>
            </div>

            <div className="form-group">
              <label>Serial Prefix</label>
              <input
                value={serialPrefix}
                onChange={(e) => setSerialPrefix(e.target.value)}
                placeholder="e.g. PROD"
                maxLength={20}
              />
              <small>Result: PROD-00000001</small>
            </div>
          </div>

          <div className="form-group checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={includeQrImage}
                onChange={(e) => setIncludeQrImage(e.target.checked)}
              />
              Include QR code images in Excel
            </label>
            <small>Adds QR image column — increases generation time</small>
          </div>

          {error && <div className="error-message">{error}</div>}

          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? "Submitting..." : "Generate QR Block"}
          </button>
        </form>
      ) : (
        <BlockProgressPoller block={block} timedOut={timedOut} blockId={createdBlockId} />
      )}
    </div>
  );
};
```

### BlockProgressPoller

```typescript
// components/BlockProgressPoller.tsx

import React from "react";
import { BlockStatusBadge } from "./BlockStatusBadge";
import { BlockDownloadButton } from "./BlockDownloadButton";
import type { Block } from "../types/block.types";

interface Props {
  block: Block | null;
  timedOut: boolean;
  blockId: string;
}

export const BlockProgressPoller: React.FC<Props> = ({ block, timedOut, blockId }) => {
  if (!block) {
    return <div className="loading-state">Queuing generation job...</div>;
  }

  return (
    <div className="block-progress">
      <h3>Block Generation</h3>

      <div className="progress-row">
        <span>Status:</span>
        <BlockStatusBadge status={block.status} />
      </div>

      <div className="progress-row">
        <span>Quantity:</span>
        <strong>{block.quantity.toLocaleString()} QR codes</strong>
      </div>

      <div className="progress-row">
        <span>Batch:</span>
        <strong>{block.batch}</strong>
      </div>

      {block.status === "in_progress" && (
        <div className="progress-indicator">
          <div className="spinner" />
          <span>Generating QR codes and building Excel file...</span>
        </div>
      )}

      {block.status === "completed" && (
        <BlockDownloadButton blockId={blockId} batch={block.batch} />
      )}

      {block.status === "failed" && (
        <div className="error-message">
          Generation failed. No credits were deducted. Please try again.
        </div>
      )}

      {timedOut && block.status !== "completed" && (
        <div className="warning-message">
          This is taking longer than expected. The file will be ready shortly —
          check the Blocks list to download when complete.
        </div>
      )}
    </div>
  );
};
```

### BlockDownloadButton

```typescript
// components/BlockDownloadButton.tsx

import React from "react";
import { useBlockDownload } from "../hooks/useBlockDownload";

interface Props {
  blockId: string;
  batch: string;
}

export const BlockDownloadButton: React.FC<Props> = ({ blockId, batch }) => {
  const { download, loading, error } = useBlockDownload();

  return (
    <div className="download-section">
      <button
        onClick={() => download(blockId, `qr_${batch}.xlsx`)}
        disabled={loading}
        className="btn-primary btn-download"
      >
        {loading ? "Preparing download..." : "Download Excel (.xlsx)"}
      </button>
      {error && <div className="error-message">{error}</div>}
      <small>Signed URL — valid for 60 minutes</small>
    </div>
  );
};
```

### BlockStatusBadge

```typescript
// components/BlockStatusBadge.tsx

import React from "react";
import type { BlockStatus } from "../types/block.types";

const COLOR_MAP: Record<BlockStatus, string> = {
  pending:     "gray",
  in_progress: "blue",
  completed:   "green",
  failed:      "red",
};

const LABEL_MAP: Record<BlockStatus, string> = {
  pending:     "Pending",
  in_progress: "In Progress",
  completed:   "Completed",
  failed:      "Failed",
};

export const BlockStatusBadge: React.FC<{ status: BlockStatus }> = ({ status }) => (
  <span className={`status-badge status-${COLOR_MAP[status]}`}>
    {LABEL_MAP[status]}
  </span>
);
```

### BlockList

```typescript
// components/BlockList.tsx

import React, { useState } from "react";
import { useBlocks } from "../hooks/useBlocks";
import { BlockStatusBadge } from "./BlockStatusBadge";
import { BlockDownloadButton } from "./BlockDownloadButton";
import { format } from "date-fns";

interface Props { productId: string; }

export const BlockList: React.FC<Props> = ({ productId }) => {
  const [page, setPage] = useState(1);
  const { data, loading, error, refetch } = useBlocks({ product_id: productId, page });

  if (loading) return <div>Loading blocks...</div>;
  if (error)   return <div className="error-message">{error}</div>;
  if (!data)   return null;

  return (
    <div className="block-list">
      <table>
        <thead>
          <tr>
            <th>Batch</th>
            <th>QR Type</th>
            <th>Quantity</th>
            <th>Status</th>
            <th>Created</th>
            <th>Download</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((block) => (
            <tr key={block.id}>
              <td>{block.batch}</td>
              <td><code>{block.qr_type}</code></td>
              <td>{block.quantity.toLocaleString()}</td>
              <td><BlockStatusBadge status={block.status} /></td>
              <td>{format(new Date(block.created_at), "MMM dd, yyyy HH:mm")}</td>
              <td>
                {block.status === "completed" ? (
                  <BlockDownloadButton blockId={block.id} batch={block.batch} />
                ) : (
                  <span className="text-muted">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.pagination.total_pages > 1 && (
        <div className="pagination">
          <button disabled={!data.pagination.has_prev} onClick={() => setPage((p) => p - 1)}>
            Previous
          </button>
          <span>Page {data.pagination.page} of {data.pagination.total_pages}</span>
          <button disabled={!data.pagination.has_next} onClick={() => setPage((p) => p + 1)}>
            Next
          </button>
        </div>
      )}
    </div>
  );
};
```

---

## QR Type Reference (display in UI)

| Code | Label       | Description                                    |
| ---- | ----------- | ---------------------------------------------- |
| D    | Dynamic     | Unique signed URL per item — standard use case |
| S    | Static      | One serial per batch, timestamp varies         |
| B    | Dual        | Two QR codes per item (covert + overt)         |
| O    | One-Time    | Deactivated after first successful scan        |
| SC   | Secure Code | QR + 12-char secret code for extra auth        |

---

## Serial Number Type Reference

| Code  | Example output  | When to use                        |
| ----- | --------------- | ---------------------------------- |
| S8DN  | PROD-00000001   | Sequential, predictable, auditable |
| S10DN | PROD-0000000001 | Sequential, larger range           |
| R6DAN | A3K9F2          | Random, harder to guess            |
| R4DAN | X7B2            | Random, short                      |

---

## UX Rules

- Show remaining QR credits prominently above the create form. Warn at < 500 remaining.
- Disable the submit button while `loading` is true.
- After submission, replace the form with `BlockProgressPoller` — do not navigate away.
- Poll every 3 seconds. After 20 failed polls, show the "check back later" message.
- The download button calls `GET /blocks/{id}/download` on every click — signed URLs expire in 60 min so never cache them.
- Show `completed_at` in the block list when available.
- `failed` blocks should show a retry option that pre-fills the form with the same values.

---

## Error Handling

| Scenario                | Code | User message                                     |
| ----------------------- | ---- | ------------------------------------------------ |
| Insufficient QR credits | 422  | "Not enough QR credits. Please top up."          |
| Product not found       | 404  | "Product not found"                              |
| Block not ready         | 409  | "File is still generating. Please wait."         |
| Download URL expired    | 403  | "Download link expired. Click again to refresh." |
| Generation failed       | —    | "Generation failed. No credits were deducted."   |

---

## Do Not

- Do not cache signed download URLs — always fetch fresh from the API
- Do not call axios directly in components — use hooks
- Do not show the download button until `block.status === "completed"`
- Do not allow the user to submit a new block while one is still in progress for the same product
- Do not skip loading and error states in any hook

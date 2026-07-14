---
title: Frontend Email Communication Module - Implementation Guide
description: Guide for building the email communication module with send and logging capabilities
tags: [frontend, email, communications, api-integration]
---

# Frontend Email Communication Module - Implementation Guide

This guide provides comprehensive instructions for building the email communication module in the frontend application.

## Overview

Build a module that allows users to:

1. Send emails with CC, HTML content, and attachments
2. View communication history/logs
3. Track email delivery status
4. Link emails to documents (quotations, invoices, etc.)

## API Endpoints Reference

### Base URL

```
http://localhost:8001/api/v1/communications
```

### Authentication

All requests require Bearer token in Authorization header:

```
Authorization: Bearer {token}
```

### Available Endpoints

1. **Send Email** - `POST /communications/send`
2. **List Communications** - `GET /communications`
3. **Get Communication** - `GET /communications/{id}`
4. **Update Status** - `PATCH /communications/{id}/status`
5. **Delete Communication** - `DELETE /communications/{id}`

## Module Structure

```
src/
├── features/
│   └── communications/
│       ├── components/
│       │   ├── EmailComposer.tsx          # Main email composition form
│       │   ├── EmailAttachments.tsx       # Attachment upload/management
│       │   ├── RecipientInput.tsx         # To/CC email inputs
│       │   ├── CommunicationList.tsx      # List of sent communications
│       │   ├── CommunicationDetail.tsx    # Single communication view
│       │   ├── CommunicationFilters.tsx   # Filter by doc type, status, etc.
│       │   └── EmailPreview.tsx           # Preview before sending
│       ├── hooks/
│       │   ├── useSendEmail.ts            # Hook for sending emails
│       │   ├── useCommunications.ts       # Hook for fetching communications
│       │   └── useEmailValidation.ts      # Email validation logic
│       ├── services/
│       │   └── communicationService.ts    # API service layer
│       ├── types/
│       │   └── communication.types.ts     # TypeScript types
│       └── utils/
│           ├── fileToBase64.ts            # File encoding utility
│           └── emailTemplates.ts          # HTML email templates
```

## TypeScript Types

```typescript
// communication.types.ts

export type DocType =
  | "quotation"
  | "sales_order"
  | "purchase_order"
  | "invoice"
  | "delivery_note"
  | "purchase_receipt"
  | "payment"
  | "rfq"
  | "material_request";

export type CommunicationChannel = "email" | "whatsapp" | "sms" | "webhook";

export type CommunicationStatus =
  | "pending"
  | "sent"
  | "delivered"
  | "failed"
  | "bounced";

export interface EmailAttachment {
  filename: string;
  content: string; // base64 encoded
  content_type?: string;
}

export interface SendEmailRequest {
  to: string;
  cc?: string[];
  subject: string;
  message: string;
  html_message?: string;
  attachments?: EmailAttachment[];
  doc_type?: DocType;
  doc_id?: string;
  doc_no?: string;
}

export interface SendEmailResponse {
  status: "sent" | "failed" | "disabled";
  message: string;
  communication_id: string | null;
}

export interface Communication {
  id: string;
  organization_id: string;
  doc_type: DocType;
  doc_id: string;
  doc_no: string | null;
  version: number;
  channel: CommunicationChannel;
  recipient_type: string | null;
  recipient: string;
  recipient_name: string | null;
  sender_id: string;
  sender_name: string | null;
  sender_email: string | null;
  subject: string | null;
  message: string | null;
  status: CommunicationStatus;
  sent_at: string | null;
  delivered_at: string | null;
  failed_at: string | null;
  error_message: string | null;
  extra_data: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface CommunicationListItem {
  id: string;
  organization_id: string;
  doc_type: DocType;
  doc_id: string;
  doc_no: string | null;
  version: number;
  channel: CommunicationChannel;
  recipient_type: string | null;
  recipient: string;
  recipient_name: string | null;
  status: CommunicationStatus;
  sent_at: string | null;
  created_at: string;
}

export interface CommunicationListResponse {
  communications: CommunicationListItem[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}
```

## API Service Implementation

```typescript
// services/communicationService.ts

import axios from "axios";
import type {
  SendEmailRequest,
  SendEmailResponse,
  Communication,
  CommunicationListResponse,
} from "../types/communication.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class CommunicationService {
  private getHeaders() {
    const token = localStorage.getItem("token"); // Adjust based on your auth
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async sendEmail(data: SendEmailRequest): Promise<SendEmailResponse> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/communications/send`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async getCommunications(params?: {
    page?: number;
    page_size?: number;
    doc_type?: string;
    doc_id?: string;
    channel?: string;
    status?: string;
    recipient_type?: string;
  }): Promise<CommunicationListResponse> {
    const response = await axios.get(`${API_BASE_URL}/api/v1/communications`, {
      headers: this.getHeaders(),
      params,
    });
    return response.data;
  }

  async getCommunication(id: string): Promise<Communication> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/communications/${id}`,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async deleteCommunication(id: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/api/v1/communications/${id}`, {
      headers: this.getHeaders(),
    });
  }
}

export const communicationService = new CommunicationService();
```

## Utility Functions

```typescript
// utils/fileToBase64.ts

export const fileToBase64 = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => {
      // Remove data:*/*;base64, prefix
      const base64 = (reader.result as string).split(",")[1];
      resolve(base64);
    };
    reader.onerror = (error) => reject(error);
  });
};

export const getContentType = (file: File): string => {
  return file.type || "application/octet-stream";
};
```

## React Hooks

```typescript
// hooks/useSendEmail.ts

import { useState } from "react";
import { communicationService } from "../services/communicationService";
import type {
  SendEmailRequest,
  SendEmailResponse,
} from "../types/communication.types";

export const useSendEmail = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [response, setResponse] = useState<SendEmailResponse | null>(null);

  const sendEmail = async (data: SendEmailRequest) => {
    setLoading(true);
    setError(null);

    try {
      const result = await communicationService.sendEmail(data);
      setResponse(result);
      return result;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || "Failed to send email";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { sendEmail, loading, error, response };
};
```

```typescript
// hooks/useCommunications.ts

import { useState, useEffect } from "react";
import { communicationService } from "../services/communicationService";
import type { CommunicationListResponse } from "../types/communication.types";

export const useCommunications = (filters?: {
  doc_type?: string;
  doc_id?: string;
  status?: string;
}) => {
  const [data, setData] = useState<CommunicationListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCommunications = async (page = 1) => {
    setLoading(true);
    try {
      const result = await communicationService.getCommunications({
        page,
        page_size: 20,
        ...filters,
      });
      setData(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch communications");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCommunications();
  }, [filters?.doc_type, filters?.doc_id, filters?.status]);

  return { data, loading, error, refetch: fetchCommunications };
};
```

## Component Examples

### Email Composer Component

```typescript
// components/EmailComposer.tsx

import React, { useState } from 'react';
import { useSendEmail } from '../hooks/useSendEmail';
import { fileToBase64, getContentType } from '../utils/fileToBase64';
import type { EmailAttachment } from '../types/communication.types';

interface EmailComposerProps {
  docType?: string;
  docId?: string;
  docNo?: string;
  defaultRecipient?: string;
  onSuccess?: (communicationId: string) => void;
}

export const EmailComposer: React.FC<EmailComposerProps> = ({
  docType,
  docId,
  docNo,
  defaultRecipient,
  onSuccess,
}) => {
  const { sendEmail, loading, error } = useSendEmail();

  const [to, setTo] = useState(defaultRecipient || '');
  const [cc, setCc] = useState<string[]>([]);
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState<EmailAttachment[]>([]);

  const handleFileUpload = async (files: FileList) => {
    const newAttachments: EmailAttachment[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const base64Content = await fileToBase64(file);

      newAttachments.push({
        filename: file.name,
        content: base64Content,
        content_type: getContentType(file),
      });
    }

    setAttachments([...attachments, ...newAttachments]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const result = await sendEmail({
        to,
        cc: cc.length > 0 ? cc : undefined,
        subject,
        message,
        attachments: attachments.length > 0 ? attachments : undefined,
        doc_type: docType as any,
        doc_id: docId,
        doc_no: docNo,
      });

      if (result.status === 'sent' && result.communication_id) {
        onSuccess?.(result.communication_id);
        // Reset form or show success message
      }
    } catch (err) {
      // Error is handled by the hook
    }
  };

  return (
    <form onSubmit={handleSubmit} className="email-composer">
      <div className="form-group">
        <label>To:</label>
        <input
          type="email"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          required
        />
      </div>

      <div className="form-group">
        <label>CC:</label>
        <input
          type="text"
          placeholder="Comma-separated emails"
          onChange={(e) => setCc(e.target.value.split(',').map(s => s.trim()))}
        />
      </div>

      <div className="form-group">
        <label>Subject:</label>
        <input
          type="text"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          required
        />
      </div>

      <div className="form-group">
        <label>Message:</label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={10}
          required
        />
      </div>

      <div className="form-group">
        <label>Attachments:</label>
        <input
          type="file"
          multiple
          onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
        />
        {attachments.map((att, idx) => (
          <div key={idx} className="attachment-item">
            {att.filename}
            <button type="button" onClick={() => {
              setAttachments(attachments.filter((_, i) => i !== idx));
            }}>Remove</button>
          </div>
        ))}
      </div>

      {error && <div className="error">{error}</div>}

      <button type="submit" disabled={loading}>
        {loading ? 'Sending...' : 'Send Email'}
      </button>
    </form>
  );
};
```

### Communication List Component

```typescript
// components/CommunicationList.tsx

import React from 'react';
import { useCommunications } from '../hooks/useCommunications';
import { format } from 'date-fns';

interface CommunicationListProps {
  docId?: string;
  docType?: string;
}

export const CommunicationList: React.FC<CommunicationListProps> = ({
  docId,
  docType,
}) => {
  const { data, loading, error, refetch } = useCommunications({
    doc_id: docId,
    doc_type: docType,
  });

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data) return null;

  return (
    <div className="communication-list">
      <h3>Communication History</h3>

      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Recipient</th>
            <th>Channel</th>
            <th>Status</th>
            <th>Document</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.communications.map((comm) => (
            <tr key={comm.id}>
              <td>{format(new Date(comm.created_at), 'MMM dd, yyyy HH:mm')}</td>
              <td>{comm.recipient}</td>
              <td>{comm.channel}</td>
              <td>
                <span className={`status-badge status-${comm.status}`}>
                  {comm.status}
                </span>
              </td>
              <td>{comm.doc_no || '-'}</td>
              <td>
                <button onClick={() => {/* View details */}}>View</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.pagination.total_pages > 1 && (
        <div className="pagination">
          <button
            disabled={!data.pagination.has_prev}
            onClick={() => refetch(data.pagination.page - 1)}
          >
            Previous
          </button>
          <span>Page {data.pagination.page} of {data.pagination.total_pages}</span>
          <button
            disabled={!data.pagination.has_next}
            onClick={() => refetch(data.pagination.page + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};
```

## Integration Examples

### Send Email from Quotation Page

```typescript
// pages/QuotationDetail.tsx

import React, { useState } from 'react';
import { EmailComposer } from '../features/communications/components/EmailComposer';

export const QuotationDetail = ({ quotation }) => {
  const [showEmailComposer, setShowEmailComposer] = useState(false);

  return (
    <div>
      <h1>Quotation {quotation.quotation_no}</h1>

      <button onClick={() => setShowEmailComposer(true)}>
        Send Email
      </button>

      {showEmailComposer && (
        <EmailComposer
          docType="quotation"
          docId={quotation.id}
          docNo={quotation.quotation_no}
          defaultRecipient={quotation.customer_email}
          onSuccess={(communicationId) => {
            console.log('Email sent:', communicationId);
            setShowEmailComposer(false);
          }}
        />
      )}
    </div>
  );
};
```

### View Communication History for Document

```typescript
// pages/QuotationDetail.tsx (continued)

import { CommunicationList } from '../features/communications/components/CommunicationList';

export const QuotationDetail = ({ quotation }) => {
  return (
    <div>
      <h1>Quotation {quotation.quotation_no}</h1>

      {/* ... other content ... */}

      <CommunicationList
        docId={quotation.id}
        docType="quotation"
      />
    </div>
  );
};
```

## Styling Recommendations

```css
/* communications.css */

.email-composer {
  max-width: 800px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.attachment-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
  background: #f5f5f5;
  border-radius: 4px;
  margin-top: 8px;
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-sent {
  background: #e8f5e9;
  color: #2e7d32;
}
.status-delivered {
  background: #e3f2fd;
  color: #1565c0;
}
.status-failed {
  background: #ffebee;
  color: #c62828;
}
.status-pending {
  background: #fff3e0;
  color: #ef6c00;
}

.communication-list table {
  width: 100%;
  border-collapse: collapse;
}

.communication-list th,
.communication-list td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
}
```

## Testing Checklist

- [ ] Send simple email (to only)
- [ ] Send email with CC
- [ ] Send email with single attachment
- [ ] Send email with multiple attachments
- [ ] Send email with HTML content
- [ ] Link email to document (quotation, invoice, etc.)
- [ ] View communication list
- [ ] Filter communications by status
- [ ] Filter communications by document
- [ ] Handle email sending errors
- [ ] Handle network errors
- [ ] Validate email addresses
- [ ] Validate required fields
- [ ] Test file size limits
- [ ] Test different file types (PDF, images, docs)

## Error Handling

```typescript
// Common error scenarios to handle

1. Invalid email address
   - Validate format before sending
   - Show inline validation errors

2. File too large
   - Check file size before encoding
   - Show user-friendly error message

3. Network error
   - Show retry option
   - Save draft locally

4. Authentication error
   - Redirect to login
   - Refresh token if expired

5. SMTP configuration error
   - Show admin contact message
   - Log error for debugging
```

## Best Practices

1. **Email Validation**: Use proper regex or library (e.g., `validator.js`)
2. **File Size Limits**: Warn users about large files (>10MB)
3. **Loading States**: Show progress for file uploads and email sending
4. **Success Feedback**: Show toast/notification on successful send
5. **Draft Saving**: Consider auto-saving drafts to localStorage
6. **Templates**: Provide pre-built email templates for common scenarios
7. **Accessibility**: Ensure form is keyboard navigable and screen-reader friendly
8. **Mobile Responsive**: Make composer work well on mobile devices

## Environment Variables

```env
# .env.local

REACT_APP_API_URL=http://localhost:8001
REACT_APP_MAX_ATTACHMENT_SIZE=10485760  # 10MB in bytes
REACT_APP_ALLOWED_FILE_TYPES=.pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg
```

## Additional Features to Consider

1. **Rich Text Editor**: Integrate TinyMCE or Quill for HTML email composition
2. **Email Templates**: Pre-built templates for quotations, invoices, etc.
3. **Scheduled Sending**: Schedule emails for later
4. **Bulk Sending**: Send to multiple recipients
5. **Email Tracking**: Track opens and clicks (requires backend support)
6. **Signature**: Add user/company signature automatically
7. **Reply/Forward**: Reply to or forward existing communications

## Support & Resources

- API Documentation: `core-service/SEND_EMAIL_API.md`
- API Documentation: `core-service/COMMUNICATIONS_API.md`
- Swagger UI: http://localhost:8001/docs
- Backend logs: `docker compose logs core-service`

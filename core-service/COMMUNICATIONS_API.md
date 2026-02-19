# Communications API

The Communications API provides a centralized logging system for all outbound communications sent to customers, suppliers, employees, and other recipients.

## Overview

Track emails, SMS, WhatsApp messages, and webhooks sent for various documents like quotations, invoices, purchase orders, and more.

## Features

- **Multi-channel support**: Email, WhatsApp, SMS, Webhook
- **Document tracking**: Link communications to specific documents (quotations, invoices, etc.)
- **Version control**: Track document version sent in each communication
- **Status tracking**: Monitor delivery status (pending, sent, delivered, failed, bounced)
- **Recipient categorization**: Classify recipients as customers, suppliers, employees, or other
- **Metadata storage**: Store additional data like template IDs, attachment links, provider IDs
- **Comprehensive filtering**: Filter by document type, channel, status, recipient type

## Endpoints

### Create Communication Log

```
POST /api/v1/communications
```

Create a new communication log entry when sending a document.

**Request Body:**

```json
{
  "doc_type": "quotation",
  "doc_id": "9bf9eecf-715b-4ed6-ab0f-3ea569bffb4d",
  "doc_no": "QTN-001",
  "version": 1,
  "channel": "email",
  "recipient_type": "customer",
  "recipient": "customer@example.com",
  "recipient_name": "John Doe",
  "sender_name": "Sales Team",
  "sender_email": "sales@company.com",
  "subject": "Quotation QTN-001",
  "message": "Please find attached quotation...",
  "metadata": {
    "template_id": "quotation_template_v1",
    "attachments": ["quotation.pdf"],
    "provider": "sendgrid",
    "provider_message_id": "msg_123456"
  }
}
```

**Response:** `201 Created`

```json
{
  "id": "c71b994c-258f-42f6-973a-c31a5fd5eb78",
  "organization_id": "bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150",
  "doc_type": "quotation",
  "doc_id": "9bf9eecf-715b-4ed6-ab0f-3ea569bffb4d",
  "doc_no": "QTN-001",
  "version": 1,
  "channel": "email",
  "recipient_type": "customer",
  "recipient": "customer@example.com",
  "recipient_name": "John Doe",
  "sender_id": "user-uuid",
  "sender_name": "Sales Team",
  "sender_email": "sales@company.com",
  "subject": "Quotation QTN-001",
  "message": "Please find attached quotation...",
  "status": "pending",
  "sent_at": null,
  "delivered_at": null,
  "failed_at": null,
  "error_message": null,
  "metadata": {
    "template_id": "quotation_template_v1",
    "attachments": ["quotation.pdf"],
    "provider": "sendgrid",
    "provider_message_id": "msg_123456"
  },
  "created_at": "2026-02-19T10:00:00Z",
  "updated_at": "2026-02-19T10:00:00Z"
}
```

### List Communications

```
GET /api/v1/communications
```

List all communication logs with optional filters.

**Query Parameters:**

- `page` (int, default: 1): Page number
- `page_size` (int, default: 20, max: 100): Items per page
- `doc_type` (string, optional): Filter by document type
- `doc_id` (UUID, optional): Filter by specific document ID
- `channel` (string, optional): Filter by channel (email, whatsapp, sms, webhook)
- `status` (string, optional): Filter by status (pending, sent, delivered, failed, bounced)
- `recipient_type` (string, optional): Filter by recipient type (customer, supplier, employee, other)
- `sort_by` (string, default: "created_at"): Sort field
- `sort_order` (string, default: "desc"): Sort order (asc, desc)

**Response:** `200 OK`

```json
{
  "communications": [
    {
      "id": "c71b994c-258f-42f6-973a-c31a5fd5eb78",
      "organization_id": "bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150",
      "doc_type": "quotation",
      "doc_id": "9bf9eecf-715b-4ed6-ab0f-3ea569bffb4d",
      "doc_no": "QTN-001",
      "version": 1,
      "channel": "email",
      "recipient_type": "customer",
      "recipient": "customer@example.com",
      "recipient_name": "John Doe",
      "status": "delivered",
      "sent_at": "2026-02-19T10:00:00Z",
      "created_at": "2026-02-19T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 1,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

### Get Communication by ID

```
GET /api/v1/communications/{communication_id}
```

Get detailed information about a specific communication log.

**Response:** `200 OK` (same structure as create response)

### Update Communication Status

```
PATCH /api/v1/communications/{communication_id}/status
```

Update the delivery status of a communication. Typically called by webhook handlers or background jobs.

**Request Body:**

```json
{
  "status": "delivered",
  "error_message": null
}
```

**Response:** `200 OK` (same structure as create response)

### Delete Communication

```
DELETE /api/v1/communications/{communication_id}
```

Delete a communication log entry.

**Response:** `204 No Content`

## Document Types

- `quotation`: Sales quotations
- `sales_order`: Sales orders
- `purchase_order`: Purchase orders
- `invoice`: Sales/Purchase invoices
- `delivery_note`: Delivery notes
- `purchase_receipt`: Purchase receipts
- `payment`: Payment records
- `rfq`: Request for Quotations
- `material_request`: Material requests

## Channels

- `email`: Email communication
- `whatsapp`: WhatsApp messages
- `sms`: SMS text messages
- `webhook`: Webhook notifications

## Status Values

- `pending`: Communication queued but not yet sent
- `sent`: Communication sent to provider
- `delivered`: Confirmed delivery to recipient
- `failed`: Delivery failed
- `bounced`: Email bounced back

## Recipient Types

- `customer`: Customer contacts
- `supplier`: Supplier contacts
- `employee`: Internal employees
- `other`: Other recipients

## Use Cases

### 1. Send Quotation via Email

```json
POST /api/v1/communications
{
  "doc_type": "quotation",
  "doc_id": "quotation-uuid",
  "doc_no": "QTN-001",
  "version": 1,
  "channel": "email",
  "recipient_type": "customer",
  "recipient": "customer@example.com",
  "recipient_name": "John Doe",
  "subject": "Quotation QTN-001",
  "metadata": {
    "template_id": "quotation_email_template",
    "attachments": ["quotation.pdf"]
  }
}
```

### 2. Send Invoice via WhatsApp

```json
POST /api/v1/communications
{
  "doc_type": "invoice",
  "doc_id": "invoice-uuid",
  "doc_no": "INV-001",
  "version": 1,
  "channel": "whatsapp",
  "recipient_type": "customer",
  "recipient": "+1234567890",
  "recipient_name": "Jane Smith",
  "message": "Your invoice INV-001 is ready",
  "metadata": {
    "whatsapp_template": "invoice_notification",
    "attachment_url": "https://example.com/invoice.pdf"
  }
}
```

### 3. Track All Communications for a Document

```
GET /api/v1/communications?doc_id=quotation-uuid
```

### 4. Monitor Failed Communications

```
GET /api/v1/communications?status=failed
```

### 5. Update Status via Webhook

```json
PATCH /api/v1/communications/{id}/status
{
  "status": "delivered"
}
```

## Integration Examples

### Email Provider Webhook Handler

```python
@app.post("/webhooks/email-provider")
async def handle_email_webhook(payload: dict):
    communication_id = payload.get("metadata", {}).get("communication_id")
    status = "delivered" if payload["event"] == "delivered" else "failed"
    error_message = payload.get("error") if status == "failed" else None

    # Update communication status
    await update_communication_status(
        communication_id,
        status,
        error_message
    )
```

### Send Document with Communication Logging

```python
async def send_quotation_email(quotation_id: UUID, recipient_email: str):
    # Send email via provider
    result = await email_provider.send(
        to=recipient_email,
        subject=f"Quotation {quotation.quotation_no}",
        template="quotation",
        attachments=["quotation.pdf"]
    )

    # Log communication
    await create_communication({
        "doc_type": "quotation",
        "doc_id": quotation_id,
        "doc_no": quotation.quotation_no,
        "channel": "email",
        "recipient": recipient_email,
        "status": "sent" if result.success else "failed",
        "metadata": {
            "provider_message_id": result.message_id
        }
    })
```

## Notes

- All timestamps are in UTC with timezone information
- The `metadata` field is flexible JSONB - store any provider-specific data
- Version tracking helps identify which document revision was sent
- Status updates are typically automated via webhooks from communication providers
- Communications are organization-scoped for multi-tenancy

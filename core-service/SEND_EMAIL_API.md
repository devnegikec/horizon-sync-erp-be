# Send Email API

The Send Email API (`POST /api/v1/communications/send`) allows you to send emails via SMTP with support for CC, HTML content, and attachments. It automatically logs all communications for tracking and audit purposes.

## Features

- Send emails via SMTP (same configuration as identity service)
- Support for CC recipients
- Plain text and HTML email bodies
- File attachments (PDF, images, documents, etc.)
- Automatic communication logging
- Base64 encoding for attachments
- Optional document linking (quotation, invoice, etc.)

## Endpoint

```
POST /api/v1/communications/send
```

## Request Body

```json
{
  "to": "customer@example.com",
  "cc": ["manager@example.com", "sales@example.com"],
  "subject": "Your Quotation QTN-001",
  "message": "Plain text email body",
  "html_message": "<html><body><h1>HTML email body</h1></body></html>",
  "attachments": [
    {
      "filename": "quotation.pdf",
      "content": "base64_encoded_content",
      "content_type": "application/pdf"
    }
  ],
  "doc_type": "quotation",
  "doc_id": "uuid",
  "doc_no": "QTN-001"
}
```

### Fields

- `to` (required): Recipient email address
- `cc` (optional): List of CC email addresses
- `subject` (required): Email subject line
- `message` (required): Plain text email body
- `html_message` (optional): HTML version of email body
- `attachments` (optional): List of file attachments
  - `filename`: Name of the file
  - `content`: Base64-encoded file content
  - `content_type`: MIME type (e.g., "application/pdf", "image/png")
- `doc_type` (optional): Document type for logging (quotation, invoice, etc.)
- `doc_id` (optional): Document UUID for logging
- `doc_no` (optional): Document number for logging

## Response

```json
{
  "status": "sent",
  "message": "Email sent successfully to customer@example.com",
  "communication_id": "c71b994c-258f-42f6-973a-c31a5fd5eb78"
}
```

### Status Values

- `sent`: Email sent successfully
- `failed`: Email sending failed
- `disabled`: Email sending is disabled in configuration

## Examples

### 1. Simple Email

```bash
curl -X POST http://localhost:8001/api/v1/communications/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "to": "customer@example.com",
    "subject": "Welcome!",
    "message": "Welcome to our service!"
  }'
```

### 2. Email with CC

```bash
curl -X POST http://localhost:8001/api/v1/communications/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "to": "customer@example.com",
    "cc": ["manager@example.com"],
    "subject": "Invoice INV-001",
    "message": "Please find your invoice attached."
  }'
```

### 3. Email with HTML

```bash
curl -X POST http://localhost:8001/api/v1/communications/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "to": "customer@example.com",
    "subject": "Welcome!",
    "message": "Welcome to our service!",
    "html_message": "<html><body><h1>Welcome!</h1><p>Welcome to our service!</p></body></html>"
  }'
```

### 4. Email with PDF Attachment

```bash
# First, encode your PDF to base64
base64 quotation.pdf > quotation.b64

# Then send the email
curl -X POST http://localhost:8001/api/v1/communications/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "to": "customer@example.com",
    "subject": "Quotation QTN-001",
    "message": "Please find attached your quotation.",
    "doc_type": "quotation",
    "doc_id": "9bf9eecf-715b-4ed6-ab0f-3ea569bffb4d",
    "doc_no": "QTN-001",
    "attachments": [
      {
        "filename": "quotation.pdf",
        "content": "'$(cat quotation.b64)'",
        "content_type": "application/pdf"
      }
    ]
  }'
```

### 5. Python Example

```python
import base64
import requests

# Read and encode file
with open("quotation.pdf", "rb") as f:
    pdf_content = base64.b64encode(f.read()).decode()

# Send email
response = requests.post(
    "http://localhost:8001/api/v1/communications/send",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    json={
        "to": "customer@example.com",
        "subject": "Quotation QTN-001",
        "message": "Please find attached your quotation.",
        "doc_type": "quotation",
        "doc_id": "9bf9eecf-715b-4ed6-ab0f-3ea569bffb4d",
        "doc_no": "QTN-001",
        "attachments": [
            {
                "filename": "quotation.pdf",
                "content": pdf_content,
                "content_type": "application/pdf"
            }
        ]
    }
)

print(response.json())
```

### 6. JavaScript/TypeScript Example

```typescript
// Read file and convert to base64
const file = await fs.readFile("quotation.pdf");
const base64Content = file.toString("base64");

// Send email
const response = await fetch(
  "http://localhost:8001/api/v1/communications/send",
  {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      to: "customer@example.com",
      subject: "Quotation QTN-001",
      message: "Please find attached your quotation.",
      doc_type: "quotation",
      doc_id: "9bf9eecf-715b-4ed6-ab0f-3ea569bffb4d",
      doc_no: "QTN-001",
      attachments: [
        {
          filename: "quotation.pdf",
          content: base64Content,
          content_type: "application/pdf",
        },
      ],
    }),
  },
);

const result = await response.json();
console.log(result);
```

## SMTP Configuration

Configure SMTP settings in your `.env` file:

```env
# Email Configuration
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@yourcompany.com
SMTP_FROM_NAME=Your Company Name
SMTP_VALIDATE_CERTS=true
```

### Common SMTP Providers

#### Gmail

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### Outlook/Office 365

```env
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
```

#### SendGrid

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

#### AWS SES

```env
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
```

## Communication Logging

Every email sent through this endpoint is automatically logged in the `communication_logs` table with:

- Recipient information
- Subject and message
- Timestamp
- Status (sent/failed)
- Attachment metadata
- Document reference (if provided)
- Error message (if failed)

You can retrieve the communication log using:

```
GET /api/v1/communications/{communication_id}
```

## Error Handling

If email sending fails, the API will:

1. Return a `failed` status
2. Log the communication with error details
3. Return the communication ID for tracking

Example error response:

```json
{
  "status": "failed",
  "message": "Failed to send email: SMTP authentication failed",
  "communication_id": "c71b994c-258f-42f6-973a-c31a5fd5eb78"
}
```

## Supported Attachment Types

Common MIME types:

- PDF: `application/pdf`
- Word: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Excel: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- Images: `image/png`, `image/jpeg`, `image/gif`
- Text: `text/plain`, `text/csv`
- ZIP: `application/zip`

The system will auto-detect content type if not provided.

## Best Practices

1. **Use HTML for rich formatting**: Provide both `message` (plain text) and `html_message` for better email client compatibility

2. **Keep attachments reasonable**: Limit attachment size to avoid email server rejections (typically < 25MB total)

3. **Link to documents**: Always provide `doc_type`, `doc_id`, and `doc_no` for proper audit trails

4. **Handle errors gracefully**: Check the response status and log communication_id for failed sends

5. **Use templates**: Create reusable HTML templates for consistent branding

6. **Test SMTP settings**: Use `EMAIL_ENABLED=false` in development to test without sending real emails

## Troubleshooting

### Email not sending

- Check `EMAIL_ENABLED=true` in .env
- Verify SMTP credentials
- Check SMTP host and port
- Review logs: `docker compose logs core-service`

### Authentication failed

- Use app-specific passwords for Gmail
- Verify username/password are correct
- Check if 2FA is enabled (requires app password)

### Attachments not working

- Ensure content is properly base64-encoded
- Check file size limits
- Verify content_type is correct

### SSL/TLS errors

- Set `SMTP_VALIDATE_CERTS=false` for self-signed certificates (not recommended for production)
- Use port 587 for STARTTLS or 465 for SSL/TLS

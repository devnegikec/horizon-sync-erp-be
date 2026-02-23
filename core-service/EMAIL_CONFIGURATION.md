# Email Configuration Guide

## Issue Fixed

The `/api/v1/communications/send` endpoint was failing with a 500 error due to:

1. **Database column mismatch**: The table had `metadata` column but code expected `extra_data`

   - **Fixed**: Renamed column from `metadata` to `extra_data`

2. **Missing SMTP configuration**: Email settings were not in `.env` file
   - **Fixed**: Added EMAIL settings with `EMAIL_ENABLED=false` by default

## Current Configuration

The service is now configured with email **disabled** by default. This means:

- API calls will succeed and log communications
- No actual emails will be sent
- Response will show `status: "disabled"`

## Testing Without SMTP

With `EMAIL_ENABLED=false`, you can test the API and it will:

- ✅ Accept the request
- ✅ Log the communication in the database
- ✅ Return success response
- ❌ NOT send actual email

Example response:

```json
{
  "status": "disabled",
  "message": "Email sending is disabled in configuration",
  "communication_id": "uuid-here"
}
```

## Enabling Email Sending

To actually send emails, update your `core-service/.env` file:

### Option 1: Gmail (Recommended for Testing)

```env
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=Horizon Sync ERP
SMTP_VALIDATE_CERTS=true
```

**Important for Gmail:**

1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password: https://myaccount.google.com/apppasswords
3. Use the App Password (not your regular password)

### Option 2: Outlook/Office 365

```env
EMAIL_ENABLED=true
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
SMTP_FROM_EMAIL=your-email@outlook.com
SMTP_FROM_NAME=Horizon Sync ERP
SMTP_VALIDATE_CERTS=true
```

### Option 3: SendGrid

```env
EMAIL_ENABLED=true
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM_EMAIL=verified-sender@yourdomain.com
SMTP_FROM_NAME=Horizon Sync ERP
SMTP_VALIDATE_CERTS=true
```

### Option 4: AWS SES

```env
EMAIL_ENABLED=true
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
SMTP_FROM_EMAIL=verified-sender@yourdomain.com
SMTP_FROM_NAME=Horizon Sync ERP
SMTP_VALIDATE_CERTS=true
```

## After Configuration

1. Update the `.env` file with your SMTP settings
2. Restart the service:
   ```bash
   docker compose restart core-service
   ```
3. Test the API - emails will now be sent!

## Verifying Configuration

Check the logs to see if email is enabled:

```bash
docker compose logs core-service | grep -i email
```

You should see:

```
Email enabled setting: True
SMTP host: smtp.gmail.com
SMTP port: 587
```

## Testing the API

```bash
curl -X POST http://localhost:8001/api/v1/communications/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Test Email",
    "message": "This is a test email from Horizon Sync ERP",
    "doc_type": "quotation",
    "doc_id": "uuid-here",
    "doc_no": "QTN-001"
  }'
```

Expected response when email is disabled:

```json
{
  "status": "disabled",
  "message": "Email sending is disabled in configuration",
  "communication_id": "uuid-here"
}
```

Expected response when email is enabled and sent successfully:

```json
{
  "status": "sent",
  "message": "Email sent successfully to recipient@example.com",
  "communication_id": "uuid-here"
}
```

## Troubleshooting

### "Connection refused" error

- SMTP server is not reachable
- Check SMTP_HOST and SMTP_PORT
- Verify firewall/network settings

### "Authentication failed" error

- Wrong username/password
- For Gmail: Use App Password, not regular password
- For SendGrid: Username must be "apikey"

### "Email not received"

- Check spam folder
- Verify sender email is verified (for AWS SES, SendGrid)
- Check email service logs/dashboard

### View detailed logs

```bash
docker compose logs -f core-service
```

## Communication Logging

Regardless of whether email is enabled or disabled, all communication attempts are logged in the `communication_logs` table with:

- Recipient information
- Subject and message
- Status (sent/failed/disabled)
- Timestamps
- Error messages (if failed)

View logs via API:

```bash
curl http://localhost:8001/api/v1/communications \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Production Recommendations

1. **Use a dedicated email service** (SendGrid, AWS SES, etc.)
2. **Set EMAIL_ENABLED=true** in production
3. **Use environment-specific credentials**
4. **Monitor email delivery rates**
5. **Set up SPF/DKIM records** for better deliverability
6. **Use verified sender domains**
7. **Implement rate limiting** to avoid spam complaints

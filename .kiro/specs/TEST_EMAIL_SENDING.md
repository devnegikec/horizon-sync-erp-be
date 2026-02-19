# Test Email Sending - Ready to Use! ✅

## Status: CONFIGURED AND READY

Your email sending is now fully configured with Gmail SMTP:

- ✅ SMTP Host: smtp.gmail.com
- ✅ SMTP Port: 587
- ✅ Username: devnegikec@gmail.com
- ✅ Password: Configured (App Password)
- ✅ EMAIL_ENABLED: true
- ✅ Service: Running

## Quick Test

### Option 1: Using Postman

1. **Get your authentication token** from your frontend or login API

2. **Send POST request** to:

   ```
   POST http://localhost:8001/api/v1/communications/send
   ```

3. **Headers:**

   ```
   Authorization: Bearer YOUR_TOKEN_HERE
   Content-Type: application/json
   ```

4. **Body (JSON):**
   ```json
   {
     "to": "devendera.negi@gmail.com",
     "subject": "Test Email from Horizon Sync ERP",
     "message": "Hello!\n\nThis is a test email from the Horizon Sync ERP Communications API.\n\nIf you receive this, the email integration is working correctly!\n\nBest regards,\nHorizon Sync Team",
     "doc_type": "quotation",
     "doc_id": "c71b994c-258f-42f6-973a-c31a5fd5eb78",
     "doc_no": "TEST-001"
   }
   ```

### Option 2: Using curl (with token)

```bash
curl -X POST http://localhost:8001/api/v1/communications/send \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "to": "devendera.negi@gmail.com",
    "subject": "Test Email from Horizon Sync ERP",
    "message": "Hello!\n\nThis is a test email.\n\nBest regards,\nHorizon Sync Team"
  }'
```

### Option 3: From Your Frontend

Use the `EmailComposer` component from the steering guide:

```typescript
import { EmailComposer } from './features/communications/components/EmailComposer';

<EmailComposer
  defaultRecipient="devendera.negi@gmail.com"
  onSuccess={(communicationId) => {
    console.log('Email sent! Communication ID:', communicationId);
  }}
/>
```

## Expected Response

### Success Response:

```json
{
  "status": "sent",
  "message": "Email sent successfully to devendera.negi@gmail.com",
  "communication_id": "uuid-here"
}
```

### If Email Fails:

```json
{
  "status": "failed",
  "message": "Failed to send email: [error details]",
  "communication_id": "uuid-here"
}
```

## Verify Email Sent

1. **Check your inbox** at devendera.negi@gmail.com
2. **Check spam folder** if not in inbox
3. **Check communication logs**:
   ```bash
   curl http://localhost:8001/api/v1/communications \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

## View Logs

To see detailed email sending logs:

```bash
docker compose logs -f core-service
```

Look for:

```
Email Service - send_email() called
SMTP Configuration:
  Host: smtp.gmail.com
  Port: 587
  Username: devnegikec@gmail.com
✅ Email 'Test Email from Horizon Sync ERP' sent successfully to devendera.negi@gmail.com
```

## Test with Attachments

```json
{
  "to": "devendera.negi@gmail.com",
  "subject": "Test Email with PDF Attachment",
  "message": "Please find the attached document.",
  "attachments": [
    {
      "filename": "test.pdf",
      "content": "JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PC9UeXBlL0NhdGFsb2cvUGFnZXMgMiAwIFI+PgplbmRvYmoKMiAwIG9iago8PC9UeXBlL1BhZ2VzL0NvdW50IDEvS2lkc1szIDAgUl0+PgplbmRvYmoKMyAwIG9iago8PC9UeXBlL1BhZ2UvTWVkaWFCb3hbMCAwIDYxMiA3OTJdL1BhcmVudCAyIDAgUi9SZXNvdXJjZXM8PC9Gb250PDwvRjEgNCAwIFI+Pj4+L0NvbnRlbnRzIDUgMCBSPj4KZW5kb2JqCjQgMCBvYmoKPDwvVHlwZS9Gb250L1N1YnR5cGUvVHlwZTEvQmFzZUZvbnQvVGltZXMtUm9tYW4+PgplbmRvYmoKNSAwIG9iago8PC9MZW5ndGggNDQ+PgpzdHJlYW0KQlQKL0YxIDI0IFRmCjEwMCA3MDAgVGQKKFNhbXBsZSBQREYpIFRqCkVUCmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDYKMDAwMDAwMDAwMCA2NTUzNSBmDQowMDAwMDAwMDE1IDAwMDAwIG4NCjAwMDAwMDAwNjAgMDAwMDAgbg0KMDAwMDAwMDExNiAwMDAwMCBuDQowMDAwMDAwMjQzIDAwMDAwIG4NCjAwMDAwMDAzMjAgMDAwMDAgbg0KdHJhaWxlcgo8PC9TaXplIDYvUm9vdCAxIDAgUj4+CnN0YXJ0eHJlZgo0MTQKJSVFT0YK",
      "content_type": "application/pdf"
    }
  ]
}
```

## Test with HTML

```json
{
  "to": "devendera.negi@gmail.com",
  "subject": "Test HTML Email",
  "message": "This is the plain text version.",
  "html_message": "<html><body><h1>Hello!</h1><p>This is an <strong>HTML</strong> email.</p><p>Best regards,<br>Horizon Sync Team</p></body></html>"
}
```

## Test with CC

```json
{
  "to": "devendera.negi@gmail.com",
  "cc": ["devnegikec@gmail.com"],
  "subject": "Test Email with CC",
  "message": "This email is sent to multiple recipients."
}
```

## Troubleshooting

### If email doesn't send:

1. **Check logs:**

   ```bash
   docker compose logs core-service | grep -i error
   ```

2. **Verify SMTP settings:**

   ```bash
   docker compose exec core-service env | grep SMTP
   ```

3. **Check Gmail App Password:**
   - Make sure 2FA is enabled on devnegikec@gmail.com
   - Verify the app password is correct: yzmfmjpyjsecjqns
   - Generate new app password if needed: https://myaccount.google.com/apppasswords

4. **Check communication logs in database:**
   ```bash
   docker compose exec postgres psql -U horizon_user -d core_db -c "SELECT id, recipient, status, error_message, created_at FROM communication_logs ORDER BY created_at DESC LIMIT 5;"
   ```

### Common Issues:

**"Authentication failed"**

- App password might be incorrect
- Regenerate app password in Google Account settings

**"Connection refused"**

- SMTP settings not loaded (restart service)
- Check EMAIL_ENABLED=true

**"Email not received"**

- Check spam folder
- Check Gmail "Sent" folder of devnegikec@gmail.com
- Verify recipient email is correct

## Next Steps

Once you confirm email sending works:

1. ✅ Test from your frontend application
2. ✅ Test sending quotations to customers
3. ✅ Test sending invoices
4. ✅ Test with attachments (PDF documents)
5. ✅ Monitor communication logs for delivery status

## Production Checklist

Before going to production:

- [ ] Use a dedicated email service (SendGrid, AWS SES, etc.)
- [ ] Set up SPF/DKIM records for your domain
- [ ] Use a verified sender domain
- [ ] Implement rate limiting
- [ ] Monitor email delivery rates
- [ ] Set up bounce handling
- [ ] Add unsubscribe links (for marketing emails)

## Support

If you need help:

1. Check logs: `docker compose logs -f core-service`
2. Review documentation: `core-service/SEND_EMAIL_API.md`
3. Check communication logs via API: `GET /api/v1/communications`

#!/bin/bash

# Get a valid token first (you'll need to replace this with your actual token)
# For now, let's just test the email sending

echo "Testing email send API..."
echo ""
echo "Payload:"
cat << 'EOF'
{
  "to": "devendera.negi@gmail.com",
  "subject": "Test Email from Horizon Sync ERP",
  "message": "Hello!\n\nThis is a test email from the Horizon Sync ERP Communications API.\n\nIf you receive this, the email integration is working correctly!\n\nBest regards,\nHorizon Sync Team",
  "doc_type": "quotation",
  "doc_id": "c71b994c-258f-42f6-973a-c31a5fd5eb78",
  "doc_no": "TEST-001"
}
EOF

echo ""
echo "Note: You need to provide a valid Bearer token to test this."
echo "Use your frontend or Postman to send this request with authentication."

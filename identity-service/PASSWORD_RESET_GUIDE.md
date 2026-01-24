# Password Reset API Guide

## Overview

The password reset functionality allows users to reset their password via a secure token-based flow.

## Endpoints

### 1. Forgot Password

**Endpoint:** `POST /api/v1/identity/forgot-password`

**Description:** Request a password reset token. For security, always returns success even if the email doesn't exist.

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response:** `200 OK`

```json
{
  "message": "If the email exists, a password reset link has been sent"
}
```

**Notes:**

- Token expires in 1 hour (configurable via `PASSWORD_RESET_TOKEN_EXPIRE_HOURS`)
- Any existing unused tokens for the user are automatically revoked
- For security, the response doesn't reveal if the email exists or not

### 2. Reset Password

**Endpoint:** `POST /api/v1/identity/reset-password`

**Description:** Reset password using the token received via email.

**Request Body:**

```json
{
  "token": "reset_token_from_email",
  "new_password": "NewSecureP@ssw0rd"
}
```

**Response:** `200 OK`

```json
{
  "message": "Password has been reset successfully. Please login with your new password."
}
```

**Password Requirements:**

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

**Error Responses:**

- `400 Bad Request` - Invalid password format

```json
{
  "detail": "Password must be at least 8 characters long"
}
```

- `401 Unauthorized` - Invalid or expired token

```json
{
  "detail": "Invalid or expired password reset token"
}
```

## Security Features

1. **Token Hashing:** Reset tokens are hashed before storage (SHA-256)
2. **Token Expiration:** Tokens expire after 1 hour
3. **Single Use:** Tokens can only be used once
4. **Session Revocation:** All refresh tokens are revoked after password reset
5. **Email Enumeration Prevention:** API doesn't reveal if email exists
6. **Rate Limiting:** Should be implemented at API gateway level

## Database Migration

Run the migration to create the `password_resets` table:

```bash
cd identity-service
alembic upgrade head
```

## Configuration

Add these environment variables to your `.env` file:

```env
# Password reset token expiration (in hours)
PASSWORD_RESET_TOKEN_EXPIRE_HOURS=1

# Email configuration (optional - for sending reset emails)
EMAIL_ENABLED=false
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=noreply@example.com
SMTP_FROM_NAME=Identity Service
```

## Email Integration (TODO)

Currently, the forgot-password endpoint generates a token but doesn't send an email. To implement email sending:

1. Install email library: `pip install aiosmtplib email-validator`
2. Create an email service in `app/services/email_service.py`
3. Update the `forgot_password` endpoint to send the email with the reset link

Example email content:

```
Subject: Password Reset Request

Hello,

You requested to reset your password. Click the link below to reset it:

https://yourapp.com/reset-password?token={reset_token}

This link will expire in 1 hour.

If you didn't request this, please ignore this email.
```

## Testing

### Test Forgot Password

```bash
curl -X POST http://localhost:8000/api/v1/identity/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

### Test Reset Password

```bash
curl -X POST http://localhost:8000/api/v1/identity/reset-password \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your_reset_token_here",
    "new_password": "NewSecureP@ssw0rd"
  }'
```

## Flow Diagram

```
User                    Frontend                Backend                 Database
 |                         |                       |                        |
 |-- Forgot Password ----->|                       |                        |
 |                         |-- POST /forgot-pwd -->|                        |
 |                         |                       |-- Generate Token ----->|
 |                         |                       |-- Store Token -------->|
 |                         |<-- Success ----------|                        |
 |<-- Email with Token ----|                       |                        |
 |                         |                       |                        |
 |-- Click Reset Link ---->|                       |                        |
 |                         |-- POST /reset-pwd --->|                        |
 |                         |   (token + new_pwd)   |-- Validate Token ----->|
 |                         |                       |-- Update Password ---->|
 |                         |                       |-- Mark Token Used ---->|
 |                         |                       |-- Revoke Sessions ---->|
 |                         |<-- Success ----------|                        |
 |<-- Success Message -----|                       |                        |
```

## Cleanup

To clean up expired tokens, you can create a scheduled task:

```python
from app.repositories.password_reset_repository import PasswordResetRepository

# Run this periodically (e.g., daily via cron)
def cleanup_expired_tokens(db: Session):
    repo = PasswordResetRepository(db)
    count = repo.delete_expired_tokens()
    print(f"Deleted {count} expired password reset tokens")
```

# Email Debugging Guide

## What I Added

I've added comprehensive logging to help debug the SMTP configuration issue:

### 1. Config Loading Logs (`app/config.py`)

- Shows when config is loaded
- Displays all SMTP settings
- Shows if .env file exists
- Shows password length (not the actual password)

### 2. Email Service Logs (`app/services/email_service.py`)

- Logs every email send attempt
- Shows SMTP connection parameters
- Shows authentication status
- Displays full error traceback if sending fails

### 3. Endpoint Logs (`app/api/v1/endpoints/auth.py`)

- Logs when forgot-password is called
- Shows the email being processed
- Tracks token generation
- Confirms background task is queued

## Step-by-Step Debugging Process

### Step 1: Restart Docker with New Logging

```bash
cd identity-service

# Stop containers
docker-compose down

# Start containers (logs will show immediately)
docker-compose up
```

**What to look for in the startup logs:**

```
Configuration Loaded
============================================================
Config file path: /app/.env
Config file exists: True/False
Environment: development
Email enabled: True/False
SMTP host: smtp.gmail.com
SMTP port: 587
SMTP username: devnegikec@gmail.com
SMTP password: SET (length: 16) or NOT SET
```

### Step 2: Check Environment Variables in Container

Run the check script:

```bash
./check-docker-env.sh
```

Or manually:

```bash
# Check if EMAIL_ENABLED is set
docker exec identity_api env | grep EMAIL_ENABLED

# Check all SMTP variables
docker exec identity_api env | grep SMTP

# Test Python config loading
docker exec identity_api python3 -c "from app.config import settings; print(f'Email enabled: {settings.email_enabled}')"
```

### Step 3: Test Forgot Password Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/identity/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "devendera.negi@gmail.com"}'
```

### Step 4: Watch the Logs

In another terminal:

```bash
docker-compose logs -f api
```

**You should see logs like this:**

```
============================================================
Forgot Password Endpoint Called
============================================================
Email: devendera.negi@gmail.com
Client IP: 192.168.65.1
Generating reset token...
Reset token generated (length: 43)
Adding email task to background...
Email task added to background queue
============================================================

============================================================
Email Service - send_email() called
============================================================
Subject: Password Reset Request
Recipient: devendera.negi@gmail.com
Body length: 234 characters
Email enabled setting: True
Email is enabled. Preparing to send...
SMTP Configuration:
  Host: smtp.gmail.com
  Port: 587
  Username: devnegikec@gmail.com
  Password: SET (length: 16)
  From Email: devnegikec@gmail.com
  From Name: Identity Service
Connection parameters: use_tls=False, start_tls=True
Using authentication (username and password provided)
Attempting to send email...
✅ Email 'Password Reset Request' sent successfully to devendera.negi@gmail.com
============================================================
```

## Common Issues and Solutions

### Issue 1: "Email disabled" in logs

**Symptom:**

```
Email disabled. Would have sent 'Password Reset Request' to ...
```

**Cause:** `EMAIL_ENABLED` is not set to `true` in the container

**Solution:**

```bash
# Check the value
docker exec identity_api env | grep EMAIL_ENABLED

# If it shows "false" or nothing, the docker-compose.yml isn't picking up .env
# Restart with explicit environment loading:
docker-compose down
docker-compose up -d

# Verify again
docker exec identity_api env | grep EMAIL_ENABLED
```

### Issue 2: "SMTP password: NOT SET"

**Symptom:**

```
SMTP password: NOT SET
No authentication credentials provided!
```

**Cause:** Password not being passed to container

**Solution:**

```bash
# Check if password is in .env file
grep SMTP_PASSWORD identity-service/.env

# Check if it's in the container
docker exec identity_api env | grep SMTP_PASSWORD

# If missing, add to docker-compose.yml environment section
# Then restart:
docker-compose down
docker-compose up -d
```

### Issue 3: SMTP Connection Errors

**Symptom:**

```
❌ Failed to send email
Error: [Errno 111] Connection refused
```

**Solutions:**

1. **Check Gmail App Password:**

   - Go to: https://myaccount.google.com/apppasswords
   - Generate a new 16-character app password
   - Update `.env` file with new password
   - Restart Docker

2. **Test SMTP from inside container:**

```bash
docker exec -it identity_api python3 -c "
import smtplib
try:
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login('devnegikec@gmail.com', 'yzmfmjpyjsecjqns')
    print('✅ SMTP connection successful!')
    s.quit()
except Exception as e:
    print(f'❌ SMTP connection failed: {e}')
"
```

3. **Check network connectivity:**

```bash
docker exec identity_api ping -c 3 smtp.gmail.com
```

### Issue 4: Config file not found

**Symptom:**

```
Config file exists: False
```

**Cause:** .env file not mounted in container

**Solution:**

Check `docker-compose.yml` volumes section:

```yaml
volumes:
  - ./app:/app/app
  - ./.env:/app/.env # Add this line if missing
```

Then restart:

```bash
docker-compose down
docker-compose up -d
```

## Quick Test Commands

### Test 1: Check if config loads correctly

```bash
docker exec identity_api python3 -c "
from app.config import settings
print('=' * 60)
print('Configuration Test')
print('=' * 60)
print(f'EMAIL_ENABLED: {settings.email_enabled}')
print(f'SMTP_HOST: {settings.smtp_host}')
print(f'SMTP_PORT: {settings.smtp_port}')
print(f'SMTP_USERNAME: {settings.smtp_username}')
print(f'SMTP_PASSWORD: {\"SET\" if settings.smtp_password else \"NOT SET\"}')
print('=' * 60)
"
```

### Test 2: Test SMTP connection

```bash
docker exec identity_api python3 -c "
import asyncio
from app.services.email_service import EmailService

async def test():
    service = EmailService()
    await service.send_email(
        subject='Test Email',
        recipient='devendera.negi@gmail.com',
        body='This is a test email from the debug script.'
    )

asyncio.run(test())
"
```

### Test 3: Check environment variables

```bash
docker exec identity_api bash -c 'echo "EMAIL_ENABLED=$EMAIL_ENABLED"'
docker exec identity_api bash -c 'echo "SMTP_HOST=$SMTP_HOST"'
docker exec identity_api bash -c 'echo "SMTP_PORT=$SMTP_PORT"'
docker exec identity_api bash -c 'echo "SMTP_USERNAME=$SMTP_USERNAME"'
```

## Expected Log Output (Success)

When everything works, you should see:

```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:app.config:============================================================
INFO:app.config:Configuration Loaded
INFO:app.config:============================================================
INFO:app.config:Config file path: /app/.env
INFO:app.config:Config file exists: True
INFO:app.config:Environment: development
INFO:app.config:Debug mode: False
INFO:app.config:Email enabled: True
INFO:app.config:SMTP host: smtp.gmail.com
INFO:app.config:SMTP port: 587
INFO:app.config:SMTP username: devnegikec@gmail.com
INFO:app.config:SMTP password: SET (length: 16)
INFO:app.config:SMTP from email: devnegikec@gmail.com
INFO:app.config:SMTP from name: Identity Service
INFO:app.config:============================================================
INFO:     Application startup complete.

[After calling forgot-password endpoint]

INFO:app.api.v1.endpoints.auth:============================================================
INFO:app.api.v1.endpoints.auth:Forgot Password Endpoint Called
INFO:app.api.v1.endpoints.auth:============================================================
INFO:app.api.v1.endpoints.auth:Email: devendera.negi@gmail.com
INFO:app.api.v1.endpoints.auth:Client IP: 192.168.65.1
INFO:app.api.v1.endpoints.auth:Generating reset token...
INFO:app.api.v1.endpoints.auth:Reset token generated (length: 43)
INFO:app.api.v1.endpoints.auth:Adding email task to background...
INFO:app.api.v1.endpoints.auth:Email task added to background queue
INFO:app.api.v1.endpoints.auth:============================================================
INFO:app.services.email_service:============================================================
INFO:app.services.email_service:Email Service - send_email() called
INFO:app.services.email_service:============================================================
INFO:app.services.email_service:Subject: Password Reset Request
INFO:app.services.email_service:Recipient: devendera.negi@gmail.com
INFO:app.services.email_service:Body length: 234 characters
INFO:app.services.email_service:Email enabled setting: True
INFO:app.services.email_service:Email is enabled. Preparing to send...
INFO:app.services.email_service:SMTP Configuration:
INFO:app.services.email_service:  Host: smtp.gmail.com
INFO:app.services.email_service:  Port: 587
INFO:app.services.email_service:  Username: devnegikec@gmail.com
INFO:app.services.email_service:  Password: SET (length: 16)
INFO:app.services.email_service:  From Email: devnegikec@gmail.com
INFO:app.services.email_service:  From Name: Identity Service
INFO:app.services.email_service:Connection parameters: use_tls=False, start_tls=True
INFO:app.services.email_service:Using authentication (username and password provided)
INFO:app.services.email_service:Attempting to send email...
INFO:app.services.email_service:✅ Email 'Password Reset Request' sent successfully to devendera.negi@gmail.com
INFO:app.services.email_service:============================================================
```

## Next Steps

1. **Restart Docker** to apply the new logging
2. **Run the check script** to verify environment variables
3. **Test the endpoint** and watch the logs
4. **Share the logs** if you still have issues

The detailed logs will show exactly where the problem is!

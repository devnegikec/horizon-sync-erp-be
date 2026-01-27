# Quick Start - Email Debugging

## What I Added

✅ **Comprehensive logging** to track every step of email sending
✅ **Config loading logs** to see what values are loaded
✅ **SMTP connection logs** to debug connection issues
✅ **Debug scripts** to test configuration

## Quick Steps to Debug

### Step 1: Restart Docker with New Logging

```bash
cd identity-service
docker-compose down
docker-compose up
```

**Watch the startup logs** - you'll see configuration being loaded with all SMTP settings.

### Step 2: Run the Debug Test Script

```bash
./test-email-debug.sh
```

This will:

- ✅ Check if environment variables are set in the container
- ✅ Test Python config loading
- ✅ Test SMTP connection
- ✅ Optionally send a test email

### Step 3: Test the Forgot Password Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/identity/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "devendera.negi@gmail.com"}'
```

### Step 4: Watch the Detailed Logs

```bash
docker-compose logs -f api | grep -A 20 "Email Service"
```

## What You'll See in Logs

### ✅ Success (Email Enabled and Working):

```
============================================================
Configuration Loaded
============================================================
Email enabled: True
SMTP host: smtp.gmail.com
SMTP port: 587
SMTP username: devnegikec@gmail.com
SMTP password: SET (length: 16)
============================================================

============================================================
Email Service - send_email() called
============================================================
Email enabled setting: True
Email is enabled. Preparing to send...
SMTP Configuration:
  Host: smtp.gmail.com
  Port: 587
  Username: devnegikec@gmail.com
  Password: SET (length: 16)
Using authentication (username and password provided)
Attempting to send email...
✅ Email 'Password Reset Request' sent successfully
============================================================
```

### ❌ Problem (Email Disabled):

```
============================================================
Configuration Loaded
============================================================
Email enabled: False  ← PROBLEM HERE
SMTP host: localhost
SMTP port: 587
SMTP username:
SMTP password: NOT SET
============================================================

Email disabled. Would have sent 'Password Reset Request'
```

## Common Issues

### Issue 1: EMAIL_ENABLED is False

**Fix:**

```bash
# Check docker-compose.yml has this line:
#   EMAIL_ENABLED: ${EMAIL_ENABLED:-false}

# Check .env file has:
#   EMAIL_ENABLED=true

# Restart:
docker-compose down
docker-compose up -d
```

### Issue 2: SMTP Variables Not Set

**Fix:**

```bash
# Verify .env file:
cat .env | grep SMTP

# Check docker-compose.yml has all SMTP variables in environment section

# Restart:
docker-compose down
docker-compose up -d
```

### Issue 3: SMTP Connection Failed

**Fix:**

```bash
# Test SMTP from inside container:
docker exec identity_api python3 -c "
import smtplib
s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
s.login('devnegikec@gmail.com', 'yzmfmjpyjsecjqns')
print('Success!')
s.quit()
"

# If this fails, check:
# 1. Gmail App Password is correct
# 2. Network connectivity: docker exec identity_api ping smtp.gmail.com
```

## Helper Scripts

1. **`./test-email-debug.sh`** - Complete diagnostic test
2. **`./check-docker-env.sh`** - Check environment variables
3. **`./restart-with-email.sh`** - Restart Docker and show logs

## Full Documentation

See `DEBUG_EMAIL_GUIDE.md` for complete troubleshooting guide.

## Need Help?

Share the output of:

```bash
./test-email-debug.sh > debug-output.txt 2>&1
docker-compose logs api > docker-logs.txt 2>&1
```

# Email Setup Fix

## Issue

Docker container is not picking up the `EMAIL_ENABLED=true` environment variable from the `.env` file.

## Solution

The `docker-compose.yml` has been updated to include all email-related environment variables. Follow these steps:

### Step 1: Stop the running containers

```bash
cd identity-service
docker-compose down
```

### Step 2: Rebuild the containers (optional but recommended)

```bash
docker-compose build --no-cache
```

### Step 3: Start the containers

```bash
docker-compose up -d
```

### Step 4: Check the logs

```bash
docker-compose logs -f api
```

You should now see email-related logs instead of "Email disabled."

## Verify Email Configuration

### Check environment variables in the container:

```bash
docker exec identity_api env | grep EMAIL
docker exec identity_api env | grep SMTP
```

You should see:

```
EMAIL_ENABLED=true
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=devnegikec@gmail.com
SMTP_PASSWORD=yzmfmjpyjsecjqns
SMTP_FROM_EMAIL=devnegikec@gmail.com
SMTP_FROM_NAME=Identity Service
```

## Test Password Reset Email

### 1. Request password reset:

```bash
curl -X POST http://localhost:8000/api/v1/identity/forgot-password \
  -H "Content-Type: application/json" \
  -d '{"email": "devendera.negi@gmail.com"}'
```

### 2. Check the logs:

```bash
docker-compose logs api | grep -i email
```

You should see:

```
INFO - Email 'Password Reset Request' sent successfully to devendera.negi@gmail.com
```

### 3. Check your email inbox

You should receive an email with the password reset link.

## Troubleshooting

### If you still see "Email disabled":

1. **Check .env file exists and has correct values:**

```bash
cat identity-service/.env | grep EMAIL
```

2. **Ensure docker-compose is reading the .env file:**

```bash
cd identity-service
docker-compose config | grep -A 10 EMAIL
```

3. **Restart with fresh environment:**

```bash
docker-compose down -v
docker-compose up -d
```

### If email sending fails:

1. **Check Gmail App Password:**

   - Make sure you're using an App Password, not your regular Gmail password
   - Generate one at: https://myaccount.google.com/apppasswords

2. **Check Gmail security settings:**

   - Enable "Less secure app access" if needed
   - Or use OAuth2 for production

3. **Check SMTP connection from container:**

```bash
docker exec -it identity_api python3 -c "
import smtplib
s = smtplib.SMTP('smtp.gmail.com', 587)
s.starttls()
s.login('devnegikec@gmail.com', 'yzmfmjpyjsecjqns')
print('SMTP connection successful!')
s.quit()
"
```

## Production Recommendations

1. **Use environment-specific .env files:**

   - `.env.development`
   - `.env.production`

2. **Use secrets management:**

   - AWS Secrets Manager
   - HashiCorp Vault
   - Docker Secrets

3. **Use a dedicated email service:**

   - SendGrid
   - AWS SES
   - Mailgun
   - Postmark

4. **Add email templates:**
   - Use HTML templates instead of plain text
   - Include branding and styling
   - Support multiple languages

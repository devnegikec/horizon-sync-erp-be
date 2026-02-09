# Cookie-Based Authentication Setup Guide

This guide explains how to set up and test the "Remember Me" feature with cookie-based authentication in both development and production environments.

## Overview

The authentication system now supports cookie-based token storage with the following features:

- **Remember Me**: Extended session duration when enabled
- **HTTP-only cookies**: Prevents XSS attacks
- **Environment-specific settings**: Different configurations for dev and prod
- **Automatic cookie management**: Tokens are automatically sent with requests

## Cookie Settings Explained

### Development Environment

```bash
COOKIE_SECURE=false        # Allows cookies over HTTP (no HTTPS required)
COOKIE_SAMESITE=lax        # Allows cookies from same site
COOKIE_HTTPONLY=true       # Prevents JavaScript access (security)
COOKIE_DOMAIN=             # Empty = current domain only
```

### Production Environment

```bash
COOKIE_SECURE=true         # Requires HTTPS
COOKIE_SAMESITE=none       # Allows cross-site cookies (with HTTPS)
COOKIE_HTTPONLY=true       # Prevents JavaScript access (security)
COOKIE_DOMAIN=.yourdomain.com  # Allows subdomains
```

## Setup Instructions

### 1. Development Setup (Local Testing)

**Step 1: Copy the development environment file**

```bash
cd identity-service
cp .env.development .env
```

**Step 2: Update database connection if needed**

```bash
# Edit .env and update DATABASE_URL if your database is different
DATABASE_URL=postgresql://horizon_user:horizon_pass@localhost:5432/identity_db
```

**Step 3: Start the service**

```bash
# Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using docker-compose
docker-compose up identity-service
```

**Step 4: Test the login with cookies**

```bash
# Login without Remember Me (session cookie)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "remember_me": false
  }' \
  -c cookies.txt \
  -v

# Login with Remember Me (persistent cookie)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "remember_me": true
  }' \
  -c cookies.txt \
  -v

# Use the cookies in subsequent requests
curl http://localhost:8000/api/v1/auth/me \
  -b cookies.txt \
  -v
```

### 2. Production Setup

**Step 1: Copy the production environment file**

```bash
cd identity-service
cp .env.production .env
```

**Step 2: Update all production values**

```bash
# Generate a strong secret key
openssl rand -hex 32

# Edit .env and update:
# - SECRET_KEY (use the generated key)
# - DATABASE_URL (production database)
# - COOKIE_DOMAIN (your domain, e.g., .yourdomain.com)
# - PASSWORD_RESET_URL (your frontend URL)
# - INVITATION_URL (your frontend URL)
# - CORS_ORIGINS (your frontend domains)
# - SMTP settings (for email)
```

**Step 3: Ensure HTTPS is configured**

Production requires HTTPS for secure cookies. Configure your reverse proxy (Nginx, Traefik, etc.) to handle SSL/TLS.

**Step 4: Deploy and test**

```bash
# Test login with HTTPS
curl -X POST https://api.yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "remember_me": true
  }' \
  -c cookies.txt \
  -v
```

## Frontend Integration

### JavaScript/TypeScript Example

```javascript
// Login function
async function login(email, password, rememberMe) {
  const response = await fetch("http://localhost:8000/api/v1/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include", // IMPORTANT: Include cookies
    body: JSON.stringify({
      email: email,
      password: password,
      remember_me: rememberMe,
    }),
  });

  if (response.ok) {
    const data = await response.json();
    console.log("Logged in:", data.user);
    // Cookies are automatically stored by the browser
    return data;
  } else {
    throw new Error("Login failed");
  }
}

// Make authenticated requests
async function getProfile() {
  const response = await fetch("http://localhost:8000/api/v1/auth/me", {
    method: "GET",
    credentials: "include", // IMPORTANT: Include cookies
  });

  if (response.ok) {
    return await response.json();
  } else {
    throw new Error("Failed to get profile");
  }
}

// Logout function
async function logout(refreshToken) {
  const response = await fetch("http://localhost:8000/api/v1/auth/logout", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include", // IMPORTANT: Include cookies
    body: JSON.stringify({
      refresh_token: refreshToken,
    }),
  });

  if (response.ok) {
    console.log("Logged out successfully");
    // Cookies are automatically cleared
  }
}
```

### React Example

```jsx
import React, { useState } from "react";

function LoginForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      const response = await fetch("http://localhost:8000/api/v1/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include", // IMPORTANT: Include cookies
        body: JSON.stringify({
          email,
          password,
          remember_me: rememberMe,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log("Login successful:", data.user);
        // Redirect to dashboard or home page
      } else {
        console.error("Login failed");
      }
    } catch (error) {
      console.error("Error:", error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Email"
        required
      />
      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        placeholder="Password"
        required
      />
      <label>
        <input
          type="checkbox"
          checked={rememberMe}
          onChange={(e) => setRememberMe(e.target.checked)}
        />
        Remember Me
      </label>
      <button type="submit">Login</button>
    </form>
  );
}

export default LoginForm;
```

### Axios Configuration

```javascript
import axios from "axios";

// Create axios instance with credentials
const api = axios.create({
  baseURL: "http://localhost:8000/api/v1",
  withCredentials: true, // IMPORTANT: Include cookies
});

// Login
async function login(email, password, rememberMe) {
  const response = await api.post("/auth/login", {
    email,
    password,
    remember_me: rememberMe,
  });
  return response.data;
}

// Get profile
async function getProfile() {
  const response = await api.get("/auth/me");
  return response.data;
}

// Logout
async function logout(refreshToken) {
  const response = await api.post("/auth/logout", {
    refresh_token: refreshToken,
  });
  return response.data;
}
```

## Cookie Behavior

### Without Remember Me (remember_me = false)

- **Access Token Cookie**: Session cookie (expires when browser closes)
- **Refresh Token Cookie**: Session cookie (expires when browser closes)
- **Use Case**: Shared computers, public devices

### With Remember Me (remember_me = true)

- **Access Token Cookie**: Expires in 30 days
- **Refresh Token Cookie**: Expires in 90 days
- **Use Case**: Personal devices, convenience

## Security Considerations

### Development

✅ **Safe for local testing**:

- `COOKIE_SECURE=false` allows HTTP
- `COOKIE_SAMESITE=lax` prevents CSRF
- `COOKIE_HTTPONLY=true` prevents XSS

### Production

✅ **Production-ready security**:

- `COOKIE_SECURE=true` requires HTTPS
- `COOKIE_SAMESITE=none` allows cross-origin (with HTTPS)
- `COOKIE_HTTPONLY=true` prevents XSS
- `COOKIE_DOMAIN` controls cookie scope

## Troubleshooting

### Cookies not being set

**Problem**: Cookies are not appearing in browser

**Solutions**:

1. Check `credentials: 'include'` in fetch/axios
2. Verify CORS settings allow credentials
3. Check browser console for CORS errors
4. Ensure `COOKIE_DOMAIN` is correct (or empty for dev)

### Cookies not being sent

**Problem**: Cookies exist but aren't sent with requests

**Solutions**:

1. Add `credentials: 'include'` to all requests
2. Check `withCredentials: true` in axios
3. Verify cookie domain matches request domain
4. Check cookie hasn't expired

### HTTPS required error

**Problem**: "Secure cookie requires HTTPS"

**Solutions**:

1. Development: Set `COOKIE_SECURE=false`
2. Production: Ensure HTTPS is configured
3. Check reverse proxy SSL settings

### Cross-origin issues

**Problem**: CORS errors with cookies

**Solutions**:

1. Add frontend origin to `CORS_ORIGINS`
2. Set `CORS_ALLOW_CREDENTIALS=true`
3. Use `COOKIE_SAMESITE=none` with HTTPS in production
4. Ensure `COOKIE_SECURE=true` when using `SAMESITE=none`

## Testing Checklist

### Development Testing

- [ ] Login without Remember Me
- [ ] Verify session cookie (no max-age)
- [ ] Close browser and verify session expired
- [ ] Login with Remember Me
- [ ] Verify persistent cookie (has max-age)
- [ ] Close browser and verify session persists
- [ ] Test logout clears cookies
- [ ] Test authenticated endpoints with cookies

### Production Testing

- [ ] Verify HTTPS is working
- [ ] Test login with Remember Me
- [ ] Verify cookies have Secure flag
- [ ] Test cross-origin requests
- [ ] Verify cookie domain is correct
- [ ] Test logout functionality
- [ ] Monitor cookie expiration

## Environment Variables Reference

| Variable                                | Development | Production        | Description          |
| --------------------------------------- | ----------- | ----------------- | -------------------- |
| `COOKIE_SECURE`                         | `false`     | `true`            | Requires HTTPS       |
| `COOKIE_SAMESITE`                       | `lax`       | `none`            | CSRF protection      |
| `COOKIE_HTTPONLY`                       | `true`      | `true`            | XSS protection       |
| `COOKIE_DOMAIN`                         | `` (empty)  | `.yourdomain.com` | Cookie scope         |
| `REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS`  | `30`        | `30`              | Access token expiry  |
| `REMEMBER_ME_REFRESH_TOKEN_EXPIRE_DAYS` | `90`        | `90`              | Refresh token expiry |

## Additional Resources

- [MDN: HTTP Cookies](https://developer.mozilla.org/en-US/docs/Web/HTTP/Cookies)
- [OWASP: Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [SameSite Cookie Explained](https://web.dev/samesite-cookies-explained/)

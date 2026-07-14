# Quick Start Guide - Remember Me Feature

## 🚀 Start in 3 Steps

### 1. Setup Environment

```bash
cd identity-service
cp .env.development .env
```

### 2. Start Service

```bash
./start-dev.sh
```

### 3. Test Feature

Open `test-login.html` in your browser or use curl:

```bash
# Login with Remember Me
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password123","remember_me":true}' \
  -c cookies.txt -v
```

## 📋 Configuration Cheat Sheet

### Development (HTTP - No HTTPS)

```bash
COOKIE_SECURE=false
COOKIE_SAMESITE=lax
```

### Production (HTTPS Required)

```bash
COOKIE_SECURE=true
COOKIE_SAMESITE=none
COOKIE_DOMAIN=.yourdomain.com
```

## 🔑 Key Points

| Feature       | Without Remember Me | With Remember Me |
| ------------- | ------------------- | ---------------- |
| Cookie Type   | Session             | Persistent       |
| Access Token  | 3 days              | 30 days          |
| Refresh Token | 7 days              | 90 days          |
| Browser Close | Expires             | Persists         |

## 💻 Frontend Code

```javascript
// IMPORTANT: Always include credentials
fetch("http://localhost:8000/api/v1/auth/login", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  credentials: "include", // ← This is required!
  body: JSON.stringify({
    email: "user@example.com",
    password: "password123",
    remember_me: true,
  }),
});
```

## 🧪 Testing

1. Open `test-login.html` in browser
2. Login with Remember Me checked
3. Close browser completely
4. Reopen and test `/me` endpoint
5. Session should still be active ✅

## 📚 Full Documentation

- **Complete Setup**: `COOKIE_SETUP_GUIDE.md`
- **Implementation Details**: `REMEMBER_ME_SETUP_COMPLETE.md`
- **API Docs**: http://localhost:8000/docs

## ⚡ Common Issues

**Cookies not working?**
→ Add `credentials: 'include'` to fetch/axios

**CORS errors?**
→ Check `CORS_ORIGINS` in `.env`

**HTTPS required error?**
→ Set `COOKIE_SECURE=false` for development

---

**Ready to go!** 🎉

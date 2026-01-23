# Quick Start Guide - Identity Service

## 🚀 Get Started in 5 Minutes

### Step 1: Clone and Navigate

```bash
cd identity-service
```

### Step 2: Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and set a strong SECRET_KEY (minimum 32 characters)
# Example: SECRET_KEY=your-super-secret-key-min-32-chars-change-this-in-production
```

### Step 3: Start with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

That's it! The service will:

1. Start PostgreSQL database
2. Run database migrations
3. Seed initial data
4. Start the API server

### Step 4: Access the Service

- **API Base URL:** http://localhost:8000
- **Interactive Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health

### Step 5: Test with Sample Credentials

Use these credentials to test the API:

**System Administrator:**

- Email: `admin@example.com`
- Password: `Admin123!`

**Regular Users:**

- Email: `john.doe@example.com` / Password: `User123!`
- Email: `jane.smith@example.com` / Password: `User123!`

## 📝 Quick API Test

### 1. Register a New User

```bash
curl -X POST "http://localhost:8000/api/v1/identity/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/v1/identity/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "Admin123!"
  }'
```

Save the `access_token` and `refresh_token` from the response.

### 3. List Users (Requires Authentication)

```bash
curl -X GET "http://localhost:8000/api/v1/identity/users" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Refresh Token

```bash
curl -X POST "http://localhost:8000/api/v1/identity/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

### 5. Logout

```bash
curl -X POST "http://localhost:8000/api/v1/identity/logout" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

## 🛠️ Development Commands

### View Logs

```bash
# All services
docker-compose logs -f

# API only
docker-compose logs -f api

# Database only
docker-compose logs -f postgres
```

### Stop Services

```bash
docker-compose down
```

### Stop and Remove Volumes (Clean Slate)

```bash
docker-compose down -v
```

### Rebuild After Code Changes

```bash
docker-compose up --build
```

### Access Database

```bash
docker exec -it identity_postgres psql -U identity_user -d identity_db
```

### Run Migrations Manually

```bash
docker exec -it identity_api alembic upgrade head
```

### Re-seed Database

```bash
docker exec -it identity_api python scripts/seed_data.py
```

## 🔍 Troubleshooting

### Port Already in Use

If port 8000 or 5432 is already in use, edit `docker-compose.yml`:

```yaml
ports:
  - "8001:8000" # Change 8000 to 8001 for API
  - "5433:5432" # Change 5432 to 5433 for PostgreSQL
```

### Database Connection Issues

1. Ensure PostgreSQL container is healthy:

   ```bash
   docker-compose ps
   ```

2. Check database logs:
   ```bash
   docker-compose logs postgres
   ```

### API Not Starting

1. Check API logs:

   ```bash
   docker-compose logs api
   ```

2. Verify environment variables in `.env`

3. Ensure SECRET_KEY is set and at least 32 characters

### Reset Everything

```bash
# Stop and remove everything
docker-compose down -v

# Remove images
docker-compose down --rmi all

# Start fresh
docker-compose up --build
```

## 📚 Next Steps

1. **Explore API Documentation:** Visit http://localhost:8000/docs
2. **Read Full README:** Check `README.md` for detailed information
3. **Review Design Document:** See `.kiro/specs/identity-microservice/design.md`
4. **Customize Configuration:** Edit `.env` for your needs
5. **Add More Users:** Use the registration endpoint or seed script

## 🎯 Production Deployment

Before deploying to production:

1. ✅ Change `SECRET_KEY` to a strong random value
2. ✅ Set `DEBUG=false`
3. ✅ Set `ENVIRONMENT=production`
4. ✅ Update `CORS_ORIGINS` to your frontend domains
5. ✅ Use strong database credentials
6. ✅ Enable HTTPS
7. ✅ Set up proper logging and monitoring
8. ✅ Configure backup strategy for PostgreSQL
9. ✅ Review and adjust token expiration times
10. ✅ Implement rate limiting

## 💡 Tips

- Use the Swagger UI at `/docs` for interactive API testing
- Access tokens expire in 15 minutes (configurable)
- Refresh tokens expire in 7 days (configurable)
- Account locks after 5 failed login attempts for 30 minutes
- All passwords must meet strength requirements

## 🆘 Need Help?

- Check the logs: `docker-compose logs -f`
- Review the design document for architecture details
- Open an issue on GitHub
- Check the health endpoint: http://localhost:8000/health

Happy coding! 🎉

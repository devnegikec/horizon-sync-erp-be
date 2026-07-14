# Master Organization Integration Guide

## 🚀 Integration Complete!

The master organization setup has been integrated into your application with multiple deployment options.

## ✅ What's Been Done:

### 1. **FastAPI Application Integration** (`core-service/app/main.py`)
- Added automatic master organization setup during application startup
- Integrated into the FastAPI `lifespan` event handler
- Production-safe error handling (fails fast in prod, warns in dev)
- Thread-safe operation with advisory locks

### 2. **Docker Integration** (`docker-compose.yml`)
- Added master organization script to core-service volumes
- Environment variables already configured (`IDENTITY_DATABASE_URL`)
- Automatic execution when core-service starts up

## 🔧 How It Works:

### **Automatic Startup (Recommended)**
When you start your core-service, it will:
1. Run database migrations
2. **Automatically setup Master Organization** (NEW!)
3. Start the FastAPI server

```bash
# Start all services - master organization setup happens automatically
docker compose up -d

# Or start just core service
docker compose up -d core-service
```

### **Manual Setup (If Needed)**
```bash
# Run standalone setup script
cd core-service
python create_master_organization.py

# Or inside running container
docker exec -it horizon_core python create_master_organization.py
```

### **CI/CD Pipeline Setup**
```yaml
# In your deployment pipeline
- name: Setup Master Organization
  run: |
    cd core-service
    python create_master_organization.py
```

## 🎯 Environment Variables:

All required environment variables are already configured in `docker-compose.yml`:

```bash
# Identity database connection (for master org)
IDENTITY_DATABASE_URL=postgresql://horizon_user:horizon_pass@postgres:5432/identity_db

# Application environment (affects error handling)
ENVIRONMENT=development  # or "production"
```

## 🔒 Thread Safety Features:

✅ **PostgreSQL Advisory Locks** - Prevents concurrent execution  
✅ **Atomic UPSERT Operations** - No race conditions  
✅ **Database Constraints** - Schema-level duplicate prevention  
✅ **Idempotent Design** - Safe to run multiple times  

## 🧪 Testing:

### **Verify Master Organization Exists:**
```bash
# Check via database
docker exec -it horizon_postgres psql -U horizon_user -d identity_db -c "
SELECT id, name, organization_type, status 
FROM organizations 
WHERE organization_type = 'master';"

# Check via API health endpoint
curl http://localhost:8001/health
```

### **Test Thread Safety:**
```bash
# Run multiple instances simultaneously - only one should succeed
python create_master_organization.py & 
python create_master_organization.py & 
python create_master_organization.py &
```

## 🚨 Error Handling:

- **Development Environment**: Logs warnings but continues startup
- **Production Environment**: Fails fast if master org setup fails
- **Database Issues**: Automatic rollback on errors
- **Duplicate Prevention**: Database constraints prevent conflicts

## 📋 Next Steps:

1. **✅ Step 1 Complete**: Master Organization auto-setup integrated
2. **🔄 Ready for Step 2**: Tell me what the next step should be!

## 🔍 Troubleshooting:

### **If Master Organization Setup Fails:**
```bash
# Check database connectivity
docker exec -it horizon_postgres pg_isready -U horizon_user -d identity_db

# Check logs
docker logs horizon_core

# Manual setup
docker exec -it horizon_core python create_master_organization.py
```

### **Reset Master Organization:**
```bash
# Remove and recreate (if needed)
docker exec -it horizon_postgres psql -U horizon_user -d identity_db -c "
DELETE FROM organizations WHERE organization_type = 'master';"

# Restart core service to auto-recreate
docker compose restart core-service
```

---

**🎉 The master organization will now be automatically created every time your application starts!**
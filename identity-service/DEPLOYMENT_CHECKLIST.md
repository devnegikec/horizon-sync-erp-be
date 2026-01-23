# Production Deployment Checklist

Use this checklist before deploying the Identity Service to production.

## 🔐 Security

- [ ] **Change SECRET_KEY** to a strong random value (min 32 characters)

  ```bash
  # Generate a secure key:
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```

- [ ] **Set DEBUG=false** in production environment

- [ ] **Use strong database credentials**
  - Change default PostgreSQL username
  - Use a strong password (20+ characters)
  - Store credentials securely (AWS Secrets Manager, HashiCorp Vault, etc.)

- [ ] **Configure CORS properly**
  - Set `CORS_ORIGINS` to your actual frontend domains
  - Remove wildcard origins
  - Verify `CORS_ALLOW_CREDENTIALS` setting

- [ ] **Enable HTTPS**
  - Use SSL/TLS certificates
  - Configure reverse proxy (Nginx, Traefik, etc.)
  - Redirect HTTP to HTTPS

- [ ] **Review token expiration times**
  - Access token: 15 minutes (default) - adjust if needed
  - Refresh token: 7 days (default) - adjust if needed

- [ ] **Implement rate limiting**
  - Add rate limiting middleware
  - Configure limits per endpoint
  - Consider using Redis for distributed rate limiting

## 🗄️ Database

- [ ] **Use managed PostgreSQL service**
  - AWS RDS, Google Cloud SQL, Azure Database, etc.
  - Enable automated backups
  - Configure backup retention policy

- [ ] **Enable SSL for database connections**
  - Update DATABASE_URL with SSL parameters
  - Verify SSL certificate validation

- [ ] **Set up database monitoring**
  - Monitor connection pool usage
  - Track query performance
  - Set up alerts for slow queries

- [ ] **Configure connection pooling**
  - Adjust `DB_POOL_SIZE` based on load
  - Set appropriate `DB_MAX_OVERFLOW`

- [ ] **Plan database backup strategy**
  - Automated daily backups
  - Point-in-time recovery enabled
  - Test restore procedures

## 🚀 Application

- [ ] **Set ENVIRONMENT=production**

- [ ] **Configure logging**
  - Set appropriate `LOG_LEVEL` (INFO or WARNING)
  - Configure log aggregation (ELK, CloudWatch, etc.)
  - Set up error tracking (Sentry, Rollbar, etc.)

- [ ] **Remove or secure development endpoints**
  - Disable /docs in production (or add authentication)
  - Disable /redoc in production (or add authentication)

- [ ] **Configure health checks**
  - Set up monitoring for /health endpoint
  - Configure uptime monitoring
  - Set up alerting

- [ ] **Optimize Docker image**
  - Verify multi-stage build is working
  - Check image size
  - Scan for vulnerabilities

## 🌐 Infrastructure

- [ ] **Use container orchestration**
  - Kubernetes, ECS, or similar
  - Configure auto-scaling
  - Set resource limits (CPU, memory)

- [ ] **Set up load balancing**
  - Configure load balancer
  - Enable health checks
  - Set up SSL termination

- [ ] **Configure DNS**
  - Set up domain name
  - Configure A/CNAME records
  - Consider CDN for static assets

- [ ] **Network security**
  - Configure security groups/firewall rules
  - Limit database access to application only
  - Use private subnets where possible

## 📊 Monitoring & Observability

- [ ] **Application monitoring**
  - Set up APM (Application Performance Monitoring)
  - Track response times
  - Monitor error rates

- [ ] **Infrastructure monitoring**
  - CPU and memory usage
  - Disk space
  - Network traffic

- [ ] **Set up alerts**
  - High error rate
  - Slow response times
  - Database connection issues
  - High CPU/memory usage

- [ ] **Log aggregation**
  - Centralized logging system
  - Log retention policy
  - Log analysis tools

## 🔄 CI/CD

- [ ] **Set up CI/CD pipeline**
  - Automated testing
  - Automated builds
  - Automated deployments

- [ ] **Configure environments**
  - Development
  - Staging
  - Production

- [ ] **Implement deployment strategy**
  - Blue-green deployment
  - Rolling updates
  - Rollback procedures

## 🧪 Testing

- [ ] **Run all tests**

  ```bash
  pytest
  ```

- [ ] **Load testing**
  - Test with expected production load
  - Identify bottlenecks
  - Verify auto-scaling works

- [ ] **Security testing**
  - Penetration testing
  - Vulnerability scanning
  - Dependency audit

- [ ] **Test disaster recovery**
  - Database restore
  - Application recovery
  - Failover procedures

## 📝 Documentation

- [ ] **Update documentation**
  - API documentation
  - Deployment procedures
  - Runbook for operations

- [ ] **Document credentials**
  - Where they're stored
  - How to rotate them
  - Who has access

- [ ] **Create incident response plan**
  - Contact information
  - Escalation procedures
  - Recovery procedures

## 🔧 Configuration

- [ ] **Environment variables checklist**

  ```bash
  # Required
  DATABASE_URL=postgresql://...
  SECRET_KEY=...

  # Application
  APP_NAME=Identity Service
  ENVIRONMENT=production
  DEBUG=false

  # Security
  ACCESS_TOKEN_EXPIRE_MINUTES=15
  REFRESH_TOKEN_EXPIRE_DAYS=7

  # CORS
  CORS_ORIGINS=https://yourdomain.com
  CORS_ALLOW_CREDENTIALS=true

  # Logging
  LOG_LEVEL=INFO
  ```

## 🎯 Performance

- [ ] **Database optimization**
  - Add indexes on frequently queried fields
  - Analyze query performance
  - Configure query caching if needed

- [ ] **Application optimization**
  - Enable response compression
  - Configure caching headers
  - Optimize database queries

- [ ] **Resource limits**
  - Set appropriate CPU limits
  - Set appropriate memory limits
  - Configure request timeouts

## 🔒 Compliance

- [ ] **Data privacy**
  - GDPR compliance (if applicable)
  - Data retention policies
  - User data deletion procedures

- [ ] **Security compliance**
  - Regular security audits
  - Dependency updates
  - Vulnerability patching

- [ ] **Audit logging**
  - Log all authentication events
  - Log all data access
  - Retain logs per compliance requirements

## 📋 Pre-Deployment Verification

Run these commands before deploying:

```bash
# 1. Build Docker image
docker build -t identity-service:latest .

# 2. Run security scan
docker scan identity-service:latest

# 3. Test with production-like config
docker-compose -f docker-compose.prod.yml up

# 4. Run health check
curl http://localhost:8000/health

# 5. Test authentication flow
# (Use your test scripts)

# 6. Check logs for errors
docker-compose logs api | grep ERROR
```

## ✅ Post-Deployment

- [ ] **Verify deployment**
  - Check health endpoint
  - Test authentication flow
  - Verify database connectivity

- [ ] **Monitor for issues**
  - Watch error logs
  - Monitor response times
  - Check resource usage

- [ ] **Update documentation**
  - Document deployment date
  - Note any issues encountered
  - Update runbook if needed

## 🚨 Rollback Plan

Have a rollback plan ready:

1. **Identify rollback trigger conditions**
   - High error rate (>5%)
   - Critical functionality broken
   - Security vulnerability discovered

2. **Rollback procedure**

   ```bash
   # Revert to previous version
   kubectl rollout undo deployment/identity-service

   # Or with Docker
   docker-compose down
   docker-compose up -d identity-service:previous-version
   ```

3. **Database rollback**

   ```bash
   # Rollback migrations if needed
   alembic downgrade -1
   ```

4. **Verify rollback**
   - Test critical functionality
   - Check error rates
   - Verify user reports

## 📞 Emergency Contacts

Document emergency contacts:

- [ ] DevOps team lead
- [ ] Database administrator
- [ ] Security team
- [ ] On-call engineer
- [ ] Product owner

## 🎉 Deployment Complete!

Once all items are checked:

1. ✅ Announce deployment to team
2. ✅ Monitor for 24-48 hours
3. ✅ Collect feedback
4. ✅ Document lessons learned
5. ✅ Plan next iteration

---

**Remember**: It's better to delay deployment than to deploy with security issues!

**Last Updated**: [Add date when you complete this checklist]
**Deployed By**: [Add your name]
**Deployment Date**: [Add deployment date]

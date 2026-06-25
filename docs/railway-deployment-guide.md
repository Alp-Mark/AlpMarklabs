# Railway Deployment Guide

**Phase G: Hardening & Traceability**  
**Last Updated**: 2026-06-20

---

## Overview

This guide covers deploying the AlpMark Intelligence Platform backend to Railway.app with production-ready configuration.

## Prerequisites

- Railway account with billing enabled
- Git repository connected to Railway
- Database credentials (Railway PostgreSQL or external)
- Environment secrets configured

---

## Quick Start

### 1. Create Railway Project

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init
```

### 2. Configure Services

**Backend Service:**
- Source: `backend/`
- Build Command: (auto-detected via Dockerfile)
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Port: `8000` (Railway will inject `$PORT`)

**Worker Service (optional):**
- Source: `worker/`
- Build Command: (auto-detected via Dockerfile)
- Start Command: `celery -A app.celery_app worker --loglevel=info`

### 3. Add PostgreSQL Database

```bash
# Add PostgreSQL plugin
railway add postgresql

# Railway automatically sets DATABASE_URL
```

### 4. Configure Environment Variables

**Required Variables:**

```bash
# Database (auto-injected by Railway PostgreSQL plugin)
DATABASE_URL=postgresql://user:pass@host:port/db

# JWT Secret (generate secure random string)
AUTH_JWT_SECRET=your-secure-secret-min-32-chars

# JWT Algorithm
AUTH_JWT_ALGORITHM=HS256

# Email Service (if using email features)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@alpmark.io

# Feature Flags (optional)
ENABLE_SIMULATIONS=true
ENABLE_CUSTOM_SEGMENTS=true

# Optimization Engine (Phase 2 Beta Launch)
# Set to "true" to enable ML-based budget optimization recommendations
# Set to "false" to disable (recommended for initial deployment)
ENABLE_OPTIMIZATION_ENGINE=false

# Frontend URL (for CORS)
FRONTEND_URL=https://your-frontend.railway.app
```

**Set via Railway CLI:**

```bash
railway variables set AUTH_JWT_SECRET="your-secret-here"
railway variables set SMTP_HOST="smtp.sendgrid.net"
# ... etc
```

Or via Railway dashboard: Project Settings → Variables

---

## Database Setup

### Run Migrations

After deploying backend service:

```bash
# Connect to Railway backend service
railway link

# Run alembic migrations
railway run alembic upgrade head
```

### Seed Demo Data

Generate demo data for 'one8' tenant:

```bash
# SSH into backend service
railway shell

# Run seed script
python scripts/seed_one8.py
```

**Expected Output:**
```
Generating 90 days of historical data...
  - Daily snapshots (cost drivers, margin, inventory, operations)...
  - Monthly cohorts (acquisition and retention)...
  - Recommendations...
  - Alert events...
  - Simulations...

Seed complete for tenant 'one8'.
  Tenant id (VITE_PYTHON_API_TENANT): 11111111-1111-4111-8111-111111111111
  Owner email (VITE_PYTHON_API_EMAIL): owner@one8.com
  Owner role: executive_owner
  Password (VITE_PYTHON_API_PASSWORD): any non-empty value
  Base currency: INR (en-IN)
  History days: 90
  Rows inserted: 2,036
```

**Test Login:**
- Email: `owner@one8.com`
- Password: any non-empty string (dev mode)

---

## Environment-Specific Configuration

### Development

```bash
# .env.development
DATABASE_URL=sqlite:///./test.db
AUTH_JWT_SECRET=dev-secret-alpmark-dev-secret-2026
ENABLE_SIMULATIONS=true
FRONTEND_URL=http://localhost:3000
```

### Staging

```bash
# Railway staging environment
DATABASE_URL=${{PostgreSQL.DATABASE_URL}}
AUTH_JWT_SECRET=${{secrets.AUTH_JWT_SECRET}}
FRONTEND_URL=https://staging-frontend.railway.app
```

### Production

```bash
# Railway production environment
DATABASE_URL=${{PostgreSQL.DATABASE_URL}}
AUTH_JWT_SECRET=${{secrets.AUTH_JWT_SECRET}}
SMTP_HOST=${{secrets.SMTP_HOST}}
SMTP_USERNAME=${{secrets.SMTP_USERNAME}}
SMTP_PASSWORD=${{secrets.SMTP_PASSWORD}}
FRONTEND_URL=https://app.alpmark.io
```

---

## Deployment Workflow

### Manual Deployment

```bash
# Deploy to Railway
railway up

# Check deployment status
railway status

# View logs
railway logs
```

### CI/CD with GitHub Actions

Railway automatically deploys on push to main branch when GitHub integration is configured.

**Optional: Manual workflow**

```yaml
# .github/workflows/railway.yml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Railway
        run: npm install -g @railway/cli
      
      - name: Deploy
        run: railway up --service backend
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

---

## Health Checks

### Backend Health

```bash
curl https://your-backend.railway.app/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "service": "alpmark-backend",
  "timestamp": "2026-06-20T12:00:00Z"
}
```

### Database Connection

```bash
railway run python -c "from backend.app.db.session import SessionLocal; db = SessionLocal(); print('DB connected')"
```

---

## Monitoring & Logs

### View Logs

```bash
# Real-time logs
railway logs --follow

# Filter by service
railway logs --service backend

# Last 100 lines
railway logs --tail 100
```

### Metrics

Railway dashboard provides:
- CPU usage
- Memory usage
- Request count
- Response times
- Error rates

---

## Scaling

### Vertical Scaling

Railway automatically scales based on your plan:
- **Starter**: 512MB RAM, 0.5 vCPU
- **Developer**: 8GB RAM, 8 vCPU
- **Team**: 32GB RAM, 32 vCPU

### Horizontal Scaling

Add replicas via Railway dashboard:
```bash
railway service scale --replicas 3
```

**Note**: Requires load balancer configuration for multiple replicas.

---

## Backup & Recovery

### Database Backups

Railway PostgreSQL includes automatic daily backups:
- Retention: 7 days (free), 30 days (paid plans)
- Point-in-time recovery available on paid plans

**Manual Backup:**

```bash
railway run pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql
```

**Restore:**

```bash
railway run psql $DATABASE_URL < backup-20260620.sql
```

### Migration Rollback

```bash
# Rollback one migration
railway run alembic downgrade -1

# Rollback to specific revision
railway run alembic downgrade <revision_id>

# View migration history
railway run alembic history
```

---

## Security Checklist

- [ ] `AUTH_JWT_SECRET` is strong random string (min 32 chars)
- [ ] Database credentials are not committed to git
- [ ] HTTPS is enabled (Railway provides this automatically)
- [ ] CORS is configured with specific frontend URLs
- [ ] Environment variables are set via Railway secrets
- [ ] Production database has restricted access
- [ ] Regular backups are enabled
- [ ] Error logs don't expose sensitive data

---

## Troubleshooting

### Database Connection Errors

**Issue**: `psycopg.OperationalError: connection failed`

**Solution**:
1. Verify `DATABASE_URL` is set: `railway variables`
2. Check PostgreSQL service is running: `railway status`
3. Test connection: `railway run python -c "from backend.app.db.session import SessionLocal; SessionLocal()"`

### Migration Errors

**Issue**: `alembic.util.exc.CommandError: Can't locate revision`

**Solution**:
```bash
# Check current revision
railway run alembic current

# Stamp database to current head
railway run alembic stamp head

# Re-run migrations
railway run alembic upgrade head
```

### Port Binding Errors

**Issue**: `OSError: [Errno 98] Address already in use`

**Solution**:
Railway injects `$PORT` variable. Ensure `uvicorn` uses it:
```python
# backend/app/main.py
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
```

### Out of Memory

**Issue**: `Killed` or `137` exit code

**Solution**:
1. Upgrade Railway plan for more RAM
2. Optimize queries (add indexes, limit result sets)
3. Enable pagination on list endpoints
4. Monitor memory usage: `railway logs | grep memory`

---

## Performance Optimization

### Database Indexes

```sql
-- Create indexes for frequently queried fields
CREATE INDEX idx_tenant_id ON recommendations(tenant_id);
CREATE INDEX idx_snapshot_date ON cost_driver_snapshots(snapshot_date);
CREATE INDEX idx_alert_created_at ON alert_event_log(created_at);
```

### Connection Pooling

SQLAlchemy pool configured in `backend/app/db/session.py`:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # Number of connections to maintain
    max_overflow=10,      # Max connections beyond pool_size
    pool_timeout=30,      # Seconds to wait for connection
    pool_recycle=1800,    # Recycle connections after 30min
)
```

### Caching

Consider adding Redis for:
- Session storage
- API response caching
- Rate limiting

```bash
# Add Redis to Railway
railway add redis

# Update environment
REDIS_URL=${{Redis.REDIS_URL}}
```

---

## Cost Optimization

Railway pricing is based on:
- **Compute**: $0.000231/GB-hour
- **Memory**: $0.000231/GB-hour
- **Egress**: $0.10/GB

**Tips**:
1. Use smaller database for staging
2. Scale down non-production services
3. Enable auto-sleep for dev environments
4. Monitor usage: `railway metrics`

---

## Next Steps

After successful deployment:

1. **Configure DNS**: Point your domain to Railway URL
2. **Enable monitoring**: Set up error tracking (Sentry, etc.)
3. **Setup CI/CD**: Configure automatic deployments
4. **Load testing**: Verify performance under load
5. **Documentation**: Update internal deployment runbook

---

## Support & Resources

- **Railway Docs**: https://docs.railway.app
- **Railway Discord**: https://discord.gg/railway
- **AlpMark Docs**: [docs/](.)
- **Issue Tracker**: Internal Jira/GitHub Issues

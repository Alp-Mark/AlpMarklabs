# AlpMark 6-Hour Auto-Refresh System

## Overview
Automated data generation system that creates realistic business activity every 6 hours to keep your demo dashboard fresh and engaging.

## What Updates Every 6 Hours

### 1. New Orders (80-120 per cycle)
- Realistic timestamps throughout the day
- 60% repeat customers, 40% new
- 1-3 items per order
- 3% return rate
- Product mix across all One8 SKUs

### 2. Ad Spend (Daily)
- **Meta Ads**: ₹20k-40k per day
- **Google Ads**: ₹15k-30k per day
- Realistic impressions and clicks
- Deduplicates if already exists for today

### 3. Snapshot Updates (All Metrics)
- Inventory risk snapshots
- Cohort retention snapshots
- Cost driver trends
- Margin drift detection
- Operational impact metrics

## Quick Commands

### Start Automation (Runs Forever)
```bash
./scripts/start_celery.sh
```

### Check Status
```bash
./scripts/celery_status.sh
```

### Stop Automation
```bash
./scripts/stop_celery.sh
```

### Trigger Manually (Don't Wait 6 Hours)
```bash
python3 scripts/trigger_demo_data.py
```

### View Real-Time Logs
```bash
# Worker log (task execution)
tail -f logs/celery_worker.log

# Beat log (scheduler)
tail -f logs/celery_beat.log
```

## Current Schedule

| Task | Frequency | Purpose |
|------|-----------|---------|
| **Demo Data Generation** | Every 6 hours | Keep dashboard fresh with new orders/spend |
| Optimization Engine | Every 6 hours | Run ML recommendations |
| Connector Sync | Every 15 minutes | Pull latest data from integrations |
| KPI Computation | Every 4 hours | Recalculate all business metrics |

## Production Deployment (Railway)

On Railway, the automation runs automatically:

1. **Worker Process**: Executes tasks
   ```
   Scale to 1 instance: $5/month
   ```

2. **Beat Process**: Schedules tasks
   ```
   Scale to 1 instance: $5/month
   ```

Both are defined in `Procfile`:
```procfile
worker: celery -A worker.app.celery_app worker --loglevel=info
beat: celery -A worker.app.celery_app beat --loglevel=info
```

### To Enable on Railway:
1. Go to your Railway project
2. Click on your service
3. Go to "Deployments" tab
4. Click "Scale"
5. Set **worker** to 1 instance
6. Set **beat** to 1 instance

## Verification

After starting automation, verify it's working:

```bash
# 1. Check services are running
./scripts/celery_status.sh

# 2. Trigger immediate run
python3 scripts/trigger_demo_data.py

# 3. Check database
psql alpmark_dev -c "SELECT COUNT(*), DATE(order_created_at) FROM shopify_orders WHERE tenant_id='23165fa5-150b-4b6c-a637-b3dd24532c4d' GROUP BY DATE(order_created_at) ORDER BY DATE(order_created_at) DESC LIMIT 5;"

# 4. View dashboard
# Visit: https://your-replit-url.replit.dev/executive/home
```

## Expected Results

### Immediate (After Manual Trigger):
- ✅ 80-120 new orders appear
- ✅ Revenue increases by ₹6-9 Lakh
- ✅ Dashboard "Updated" timestamp refreshes
- ✅ All 7 KPI cards recalculate

### After 6 Hours (Automatic):
- ✅ New batch of orders created
- ✅ Ad spend for new day added
- ✅ Metrics continue evolving
- ✅ Revenue growth trends emerge

### After 2-3 Days:
- ✅ Growth rates become meaningful (comparing periods)
- ✅ Trends visible in charts
- ✅ Realistic business simulation complete

## Monitoring

### Local Development:
```bash
# Watch worker execute tasks
tail -f logs/celery_worker.log

# Watch scheduler trigger tasks
tail -f logs/celery_beat.log
```

### Production (Railway):
```bash
# View worker logs
railway logs --service worker

# View beat logs  
railway logs --service beat
```

## Troubleshooting

### ❌ "Redis not running"
```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis
```

### ❌ "Tasks not executing"
```bash
# Check beat is scheduling
grep "demo-data-generation" logs/celery_beat.log

# Check worker is receiving
grep "Task worker.app.tasks_demo_data" logs/celery_worker.log
```

### ❌ "No new orders appearing"
```bash
# Trigger manually to test
python3 scripts/trigger_demo_data.py

# Check for errors
tail -50 logs/celery_worker.log
```

## Architecture

```
┌─────────────┐
│  Beat       │  Scheduler (cron-like)
│  Scheduler  │  Triggers tasks at intervals
└──────┬──────┘
       │ Every 6h
       ↓
┌─────────────┐
│   Redis     │  Message Queue
│   Broker    │  Holds task messages
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Celery     │  Worker (executor)
│  Worker     │  Runs demo_data_generation task
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Postgres   │  Database
│  Database   │  Stores orders, line items, ad spend
└─────────────┘
```

## Cost

**Local Development**: Free
- Redis runs locally
- PostgreSQL runs locally
- Celery runs in background

**Production (Railway)**:
- Worker: ~$5/month (1 instance)
- Beat: ~$5/month (1 instance)
- **Total**: ~$10/month for 24/7 automation

## Next Steps

1. ✅ Start local automation: `./scripts/start_celery.sh`
2. ✅ Test immediately: `python3 scripts/trigger_demo_data.py`
3. ✅ Deploy to Railway: Scale worker + beat to 1 instance each
4. ✅ Monitor dashboard: Watch metrics evolve every 6 hours
5. ✅ Demo to stakeholders: Show living, breathing business intelligence

---

**Status**: ✅ Fully automated
**Last Updated**: 2026-06-25
**Maintainer**: AlpMark Engineering Team

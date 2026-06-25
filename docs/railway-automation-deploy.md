# Deploy 6-Hour Automation to Railway

## Steps to Deploy

### 1. Commit and Push Code Changes

```bash
# Add all new files
git add worker/app/tasks_demo_data.py
git add worker/app/celery_app.py
git add scripts/*.sh
git add scripts/trigger_demo_data.py
git add docs/automation-guide.md

# Commit
git commit -m "Add 6-hour automated data generation for demo dashboard"

# Push to main
git push origin main
```

### 2. Railway Auto-Deploys

Railway will automatically:
- ✅ Detect code changes
- ✅ Rebuild your containers
- ✅ Deploy new worker code

### 3. Scale Worker + Beat Processes

Go to Railway dashboard and scale:

**Worker Process:**
1. Click on your service
2. Go to "Settings" → "Service"  
3. Find `worker` process in Procfile
4. Scale to **1 instance**
5. Estimated cost: ~$5/month

**Beat Process:**
1. Same steps
2. Find `beat` process in Procfile
3. Scale to **1 instance**
4. Estimated cost: ~$5/month

### 4. Verify It's Working

```bash
# View worker logs on Railway
railway logs --service your-service-name | grep demo-data

# Or in Railway dashboard:
# Click service → "Deployments" → "View Logs"
# Look for: "Demo data generated: {'orders_created': ...}"
```

### 5. Monitor Production

Your production dashboard will now:
- ✅ Generate 80-120 orders every 6 hours
- ✅ Add daily ad spend automatically
- ✅ Keep metrics fresh 24/7
- ✅ Show realistic business growth

## What Happens After Deploy?

**Immediate (First 6 hours):**
- Railway deploys new code
- Worker + beat start running
- First data generation in ~6 hours

**After First Run:**
- Dashboard shows new orders
- Revenue increases
- Metrics recalculate
- Timestamp shows "Updated X minutes ago"

**After 2-3 Days:**
- Growth trends become visible
- Historical comparison works
- Demo looks like real business

## Cost Breakdown

| Component | Cost/Month |
|-----------|------------|
| Web service (already running) | $5 |
| Worker process (new) | $5 |
| Beat scheduler (new) | $5 |
| PostgreSQL (existing) | Included |
| Redis (new) | Add-on ~$3 |
| **Total** | **~$18/month** |

## Alternative: Keep Local Only

If you want to save costs for now:

**Option A: Manual Trigger**
```bash
# Run this whenever you want fresh data
python3 scripts/trigger_demo_data.py
```

**Option B: Local Automation + Railway Web Only**
- Keep automation running on your local machine
- Point local automation to Railway production database
- Railway only runs web API (no worker costs)

## Recommended Approach

**For Development/Testing:**
- ✅ Run automation locally
- ✅ No git push needed
- ✅ Free!

**For Demo/Production:**
- ✅ Push to git
- ✅ Scale worker + beat on Railway
- ✅ 24/7 automated fresh data
- ✅ ~$18/month total

---

**Current Status**: Running locally ✅  
**Ready to Deploy**: Yes, commit + push + scale processes ✅

# Railway Deployment - NEXT STEPS

✅ **Code Pushed to GitHub** (commit: 072d2f1)

## Railway Will Auto-Deploy

Railway monitors your `main` branch and will automatically:
1. Detect the new commit
2. Rebuild your containers with the new code
3. Deploy the updated services

**Check deployment status:**
```bash
railway status
```

Or go to: https://railway.app → Your Project → "Deployments" tab

## CRITICAL: Scale Worker + Beat Processes

After auto-deploy completes, you MUST manually scale these processes:

### Option A: Railway Dashboard (Recommended)

1. Go to https://railway.app
2. Click your project
3. Click on your service  
4. Go to "Settings" → "Deploy"
5. Find the Procfile configuration
6. Scale these processes to **1 instance each**:
   - `worker` → 1 instance ($5/month)
   - `beat` → 1 instance ($5/month)

### Option B: Railway CLI

```bash
# Scale worker process
railway up worker=1

# Scale beat scheduler
railway up beat=1
```

## Verify It's Working

### 1. Check Logs

```bash
# Watch worker logs
railway logs --service your-service-name | grep demo-data

# Or in dashboard:
# Click service → "Deployments" → View latest deploy → "Logs"
```

Look for this message every 6 hours:
```
✅ Demo data generated: {'orders_created': 104, 'line_items_created': 159, ...}
```

### 2. Test Manually

Once deployed, trigger immediately (don't wait 6 hours):

```bash
# SSH into Railway container
railway run python3 scripts/trigger_demo_data.py
```

### 3. Check Dashboard

Visit your production frontend:
- https://your-replit-url.replit.dev/executive/home
- Refresh every few minutes
- Revenue should increase
- "Updated X minutes ago" timestamp should refresh

## Expected Timeline

| Time | Event |
|------|-------|
| Now | Code pushed to GitHub ✅ |
| +2-5 min | Railway auto-deploys new code |
| +6 min | Scale worker + beat to 1 instance |
| +12 min | First automatic data generation |
| Every 6h | New orders + ad spend generated |

## Cost Breakdown

| Service | Instances | Cost/Month |
|---------|-----------|------------|
| Web (existing) | 1 | $5 |
| **Worker (NEW)** | **1** | **$5** |
| **Beat (NEW)** | **1** | **$5** |
| PostgreSQL | Shared | Included |
| Redis (if needed) | Add-on | ~$3 |
| **Total** | - | **~$18/month** |

## Troubleshooting

### ❌ "Worker not starting"

Check Railway logs for errors:
```bash
railway logs --service worker
```

Common issues:
- Redis not configured (need Redis add-on)
- Database connection error (check DATABASE_URL env var)
- Missing dependencies (check requirements.txt deployed)

### ❌ "No new orders appearing"

1. Check beat scheduler is running:
   ```bash
   railway logs | grep "Scheduler: Sending due task"
   ```

2. Check worker received task:
   ```bash
   railway logs | grep "Task worker.app.tasks_demo_data"
   ```

3. Manually trigger to test:
   ```bash
   railway run python3 scripts/trigger_demo_data.py
   ```

### ❌ "Dashboard still shows old data"

- Frontend cache: Hard refresh (Cmd+Shift+R or Ctrl+Shift+F5)
- Backend hasn't refreshed: Wait 6 hours or trigger manually
- Database not connected: Check Railway DATABASE_URL matches

## Next Steps After Deploy

1. ✅ Monitor first automatic run (in 6 hours)
2. ✅ Verify dashboard metrics update
3. ✅ Check logs for any errors
4. ✅ Add Redis add-on if not already present:
   ```bash
   railway add redis
   ```
5. ✅ Set REDIS_URL environment variable to use Railway Redis

## Success Criteria

✅ Worker process running (1 instance)
✅ Beat process running (1 instance)  
✅ Logs show "Demo data generated" every 6 hours
✅ Dashboard revenue increases over time
✅ Dashboard timestamp shows "Updated X minutes ago"
✅ No errors in Railway logs

---

**Current Status**: Waiting for Railway auto-deploy
**Next Action**: Scale worker + beat to 1 instance each
**Timeline**: ~10 minutes from code push to full automation live

Want me to help monitor the deployment or troubleshoot any issues?

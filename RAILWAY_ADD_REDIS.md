# Add Redis to Railway - REQUIRED for Celery Automation

## Why Redis is Needed

Celery requires a message broker to:
- Queue tasks (demo data generation)
- Schedule recurring jobs (every 6 hours)
- Coordinate between beat scheduler and worker

Without Redis, the automation **will not work** on Railway.

## Option 1: Railway Redis Plugin (Recommended)

**Cost**: Free tier available (512MB), then $5/month

**Steps**:
1. Go to https://railway.app
2. Click your project
3. Click "+ New" → "Database" → "Add Redis"
4. Railway auto-creates Redis service
5. Railway auto-sets `REDIS_URL` environment variable
6. Redeploy your service (or it auto-redeploys)

**That's it!** Your code already uses `REDIS_URL`, so it will automatically connect.

## Option 2: External Redis (Upstash, Redis Cloud)

If you want to use an external Redis provider:

**Upstash** (Recommended - has free tier):
1. Go to https://upstash.com
2. Create free account
3. Create Redis database
4. Copy the Redis URL
5. In Railway → Your Service → Variables → Add:
   ```
   REDIS_URL=redis://your-upstash-url
   ```

**Redis Cloud**:
1. Go to https://redis.com/cloud
2. Sign up for free tier (30MB free)
3. Create database
4. Copy connection URL
5. Add to Railway environment variables

## Option 3: Skip Redis (Local Development Only)

**For testing without automation**:
- Automation won't work
- Web API will work fine
- You can trigger manually with scripts

**Not recommended for production demo!**

## Verify Redis is Working

After adding Redis to Railway:

### 1. Check Environment Variable

```bash
railway variables
```

Should show:
```
REDIS_URL=redis://...
```

### 2. Check Worker Logs

```bash
railway logs | grep -i redis
```

Should show:
```
[INFO] Connected to redis://...
```

### 3. Check Beat Scheduler

```bash
railway logs | grep "Scheduler: Sending due task"
```

Should show tasks being scheduled.

## Troubleshooting

### ❌ "Connection refused to Redis"

- Check REDIS_URL is set: `railway variables`
- Check Redis service is running: Railway dashboard → Redis service → Status
- Check worker has access: Variables should be shared across services

### ❌ "No such table 'celerybeat_schedule'"

- This is normal! Celery creates this automatically
- If using Railway Redis plugin, it handles this

### ❌ "Tasks not executing"

- Check worker is scaled to 1 instance
- Check beat is scaled to 1 instance
- Check both have access to same REDIS_URL

## Cost Comparison

| Option | Free Tier | Paid |
|--------|-----------|------|
| Railway Redis Plugin | 512MB free | $5/month after |
| Upstash | 10k commands/day | $0.20 per 100k commands |
| Redis Cloud | 30MB free | $5/month |

**Recommendation**: Use Railway Redis Plugin for simplicity.

## Current Status

- ✅ Local development: Redis running (localhost)
- ❌ Railway production: **Need to add Redis**
- ✅ Code ready: Uses `REDIS_URL` env var

## Next Steps

1. **Add Railway Redis Plugin** (2 minutes)
2. **Verify REDIS_URL is set** (`railway variables`)
3. **Scale worker + beat to 1 instance** (Settings → Deploy)
4. **Check logs** for "Connected to redis"
5. **Wait 6 hours** or trigger manually

---

**Without Redis, the 6-hour automation will NOT work on Railway!**

Add it now: https://railway.app → Your Project → "+ New" → "Add Redis"

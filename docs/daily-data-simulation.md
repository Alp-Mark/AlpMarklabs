# Daily Data Simulation for One8 Tenant

## Overview

Simulates continuous Shopify and ad platform data ingestion by generating realistic daily data for the One8 tenant. This allows testing the optimization engine and dashboards with a growing, realistic dataset without needing actual platform connections.

## What It Does

The daily simulator generates:
- **Orders**: 150-350 orders/day (30% more on weekends)
- **Refunds**: 12% of orders from 3-10 days ago
- **Meta Ad Spend**: ₹150K-250K/day across 3 campaigns
- **Google Ad Spend**: ₹80K-150K/day across 3 campaigns

All data follows realistic business patterns (day of week, order values, etc.)

## Usage

### Manual Testing

```python
from worker.app.daily_data_simulator import run_daily_simulation
from datetime import date, timedelta

# Generate data for tomorrow
tomorrow = date.today() + timedelta(days=1)
result = run_daily_simulation(target_date=tomorrow)

# Backfill a date range
from worker.app.daily_data_simulator import simulate_date_range

result = simulate_date_range(
    start_date=date(2026, 6, 1),
    end_date=date(2026, 6, 30)
)
```

### Production (Celery Beat)

The simulator runs automatically as a Celery Beat task **once per day** when enabled.

**Enable in Railway:**
```bash
ENABLE_DAILY_DATA_SIMULATION=true
```

**Disable (default):**
```bash
ENABLE_DAILY_DATA_SIMULATION=false
```

## Generated Data Details

### Orders
- **Volume**: 150-350/day (weekdays), 195-455/day (weekends)
- **AOV**: ₹6,500 avg with ₹3,000 std dev (log-normal distribution)
- **Fulfillment**: 92% fulfilled, 5% pending, 3% cancelled
- **Timestamp**: Random distribution throughout the day

### Refunds
- **Rate**: 12% of orders
- **Delay**: 3-10 days after order
- **Reasons**: customer_request, defective, size_issue, changed_mind

### Meta Ad Spend
- **Daily Total**: ₹150K-250K
- **Campaigns** (equal split):
  - TOF_Prospecting_Lookalike
  - MOF_Retargeting_Engagement
  - BOF_Conversion_Purchase

### Google Ad Spend
- **Daily Total**: ₹80K-150K
- **Campaigns** (equal split):
  - Search_Brand_One8
  - Search_Generic_Sportswear
  - Display_Prospecting_Sports

## Celery Beat Schedule

- **Task**: `worker.app.tasks.run_daily_data_simulation_schedule`
- **Schedule**: Once per day (24 hours)
- **Behavior**: Automatically skips if data already exists for today

## Testing the Feature

1. **Check schedule is registered:**
   ```bash
   celery -A worker.app.celery_app inspect scheduled
   ```

2. **Run manually:**
   ```bash
   export ENABLE_DAILY_DATA_SIMULATION=true
   export DATABASE_URL="postgresql://..."
   python3 -c "from worker.app.tasks import run_daily_data_simulation_schedule; print(run_daily_data_simulation_schedule())"
   ```

3. **Verify data created:**
   ```sql
   SELECT 
       order_created_at::date as date,
       COUNT(*) as orders,
       SUM(total_amount) as revenue
   FROM shopify_orders
   WHERE tenant_id = '23165fa5-150b-4b6c-a637-b3dd24532c4d'
   GROUP BY order_created_at::date
   ORDER BY date DESC
   LIMIT 7;
   ```

## Benefits

1. **Realistic Testing**: Continuous data growth mimics production environment
2. **Optimization Validation**: Ever-growing dataset allows testing optimization improvements over time
3. **Dashboard Testing**: Metrics and charts update daily with fresh data
4. **No Platform Dependencies**: Works without actual Shopify/Meta/Google connections

## Safety Features

- **Duplicate Prevention**: Automatically skips dates that already have data
- **Environment Gated**: Must explicitly enable via environment variable
- **Error Handling**: Graceful failure with detailed error messages
- **Transaction Safety**: Uses database transactions to ensure data consistency

## Files

- `worker/app/daily_data_simulator.py` - Core simulation logic
- `worker/app/tasks.py` - Celery task wrapper
- `worker/app/celery_app.py` - Beat schedule configuration

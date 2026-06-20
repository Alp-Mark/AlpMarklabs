# Phase F: Historical Demo Data

**Status**: ✅ COMPLETE (880 tests passing, ruff+mypy clean)

## Overview

Extended `scripts/seed_one8.py` to generate 90-365 days of historical data across all snapshot types and updated the one8 owner role to `executive_owner` so they see all dashboard sections under the new navigation rules.

## What Changed

### 1. Owner Role Updated
- **Before**: `OWNER_ROLE = "brand_admin"`
- **After**: `OWNER_ROLE = "executive_owner"`
- **Why**: Executive Owner role grants access to all dashboard sections in the new E8 navigation menu

### 2. Historical Data Window
- **New constant**: `HISTORY_DAYS = 90` (configurable from 90-365 days)
- **What gets history**:
  - ✅ Cost driver snapshots (daily, 90 days)
  - ✅ Margin drift snapshots (daily, 90 days)
  - ✅ Inventory risk snapshots (daily, 90 days)
  - ✅ Operational impact snapshots (daily, 90 days)
  - ✅ Acquisition cohorts (monthly, 6 months) - *already had history*
  - ✅ Cohort snapshots (monthly, 6 months) - *already had history*
  - Recommendations (current/recent 30 days)
  - Alert events (current/recent 4 days)
  - Simulations (current/recent 2 days)

### 3. Builder Function Updates
All snapshot builders now accept:
- `snapshot_date: date` - The date for this snapshot
- `day_offset: int = 0` - Used to vary data realistically across days

**Updated functions**:
```python
build_cost_drivers(snapshot_date, now, day_offset) 
build_margin_drift(snapshot_date, day_offset)
build_inventory_risk(snapshot_date, day_offset)
build_operational_impact(snapshot_date, day_offset)
```

### 4. Realistic Data Variance
Each builder adds small daily variance to simulate realistic business fluctuations:
- **Cost drivers**: ±2% variance based on day_offset
- **Margin drift**: ±1pt margin variance
- **Inventory risk**: -10% inventory reduction over full history window
- **Operational impact**: ±10% velocity variance

### 5. Seed Output
The script now shows progress as it generates data:
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

## How to Re-Seed Railway

### Prerequisites
1. Railway database must be up and running
2. Alembic migrations must be current
3. Database connection string in environment

### Step 1: Configure History Window (Optional)
Edit `scripts/seed_one8.py` line ~90:
```python
HISTORY_DAYS = 90  # Change to 180 or 365 for more history
```

**Note**: More history = more rows:
- 90 days: ~2,000 rows
- 180 days: ~3,600 rows  
- 365 days: ~7,300 rows

### Step 2: Run Seed Script
From Railway's terminal or locally with Railway database URL:

```bash
cd /path/to/alpmark
export DATABASE_URL="postgresql://user:pass@host:port/db"  # Railway URL
python3 scripts/seed_one8.py
```

### Step 3: Verify Seed
The script should output:
```
Seed complete for tenant 'one8'.
  Owner role: executive_owner
  History days: 90
  Rows inserted: 2,036
```

### Step 4: Test Frontend
1. Login as `owner@one8.com` with any password
2. Select one8 tenant
3. Navigate to Dashboard - you should now see:
   - Time-series charts with 90 days of history
   - Trend lines showing realistic variance
   - All navigation menu items (Intelligence + Admin sections)

## Quality Gates

All three gates passed:

### Ruff (Linting)
```bash
python3 -m ruff check scripts/seed_one8.py
# Result: All checks passed!
```

### Mypy (Type Checking)
```bash
python3 -m mypy scripts/seed_one8.py
# Result: Success: no issues found in 1 source file
```

### Pytest (Full Test Suite)
```bash
python3 -m pytest backend/tests/ -x
# Result: 880 passed, 1 skipped, 217 warnings in 47.75s
```

## Data Characteristics

### Cost Drivers (5 types × 90 days = 450 rows)
- COGS: ~42% of revenue ±2%
- Shipping: ~6% of revenue ±2%
- Returns: ~8% of revenue ±2%
- Discounts: ~5% of revenue ±2%
- Ad Spend: ~18% of revenue ±2%

### Margin Drift (4 channel×category combos × 90 days = 360 rows)
- Shopify/Running: 38.5% ±1pt
- Meta Ads/Casual: 41.2% ±1pt
- Google Ads/Training: 36.0% ±1pt
- Shopify/Formal: 47.0% ±1pt

### Inventory Risk (7 SKUs × 90 days = 630 rows)
- Inventory depletes 10% over the full history window
- Velocity varies ±10% day-to-day
- All SKUs (ONE8-RUN-001, ONE8-RUN-002, ONE8-CAS-001, etc.)

### Operational Impact (7 SKUs × 90 days = 630 rows)
- Daily velocity varies ±10%
- Return rates stable at SKU baseline ±2%
- Logistics cost per unit stable

### Acquisition Cohorts (3 channels × 6 months = 18 rows)
- Shopify Organic
- Meta Ads
- Google Ads

### Cohort Snapshots (6 months × 3 windows = 18 rows)
- 30-day, 60-day, 90-day observation windows

## Known Limitations

1. **Recommendations**: Still single-day generation (not spread across history)
   - Reason: Recommendations are action-oriented and less historical
   - Future: Could be extended if needed

2. **Alert Events**: Still recent 4 days only
   - Reason: Alerts are time-sensitive notifications
   - Future: Could generate historical alerts for closed incidents

3. **Simulations**: Still recent 2 days only
   - Reason: Simulations are manual user-created scenarios
   - Future: Could generate more scenarios if needed

4. **Database Size**: 90 days creates ~2K rows
   - Not a concern for demo data
   - For production: need data archival strategy

## Next Phase

**Phase G**: Hardening & Traceability
- Full ruff/mypy/pytest validation
- Endpoint-to-screen mapping matrix
- Documentation completeness check

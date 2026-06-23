# AlpMark Executive Owner Frontend - Complete Implementation Guide

**Version 1.0**  
**Created: 2026-06-22**  
**Persona: Executive Owner (Strategic Business Decision-Maker)**

---

## Table of Contents

1. [Executive Owner Role Overview](#executive-owner-role-overview)
2. [Pages Required](#pages-required)
3. [API Endpoints Reference](#api-endpoints-reference)
4. [Data Models](#data-models)
5. [Component Specifications](#component-specifications)
6. [Page Implementations](#page-implementations)
7. [Navigation & Routing](#navigation--routing)
8. [Step-by-Step Build Instructions](#step-by-step-build-instructions)

---

## Executive Owner Role Overview

### Who is Executive Owner?

**Executive Owner** is the **highest-authority customer user** in a tenant — typically the CEO, Founder, or General Manager of the D2C e-commerce brand. They are accountable for business profitability and strategic direction.

### What Executive Owner Can Do

✅ **View unified business health dashboard** (revenue, profit, contribution margin, trends)  
✅ **See all 7 Step-2 KPIs** with drift indicators vs targets  
✅ **Review prioritized alerts** ranked by business impact  
✅ **View and approve/reject strategic recommendations**  
✅ **Run strategic simulations** (what-if scenarios)  
✅ **View cross-team performance roll-up** (Growth, Retention, Finance, Operations)  
✅ **Set and update business KPI targets**  
✅ **Configure alert preferences** (thresholds, recipients, escalation rules)  
✅ **Delegate recommendation approval authority** to qualified users  
✅ **View billing and subscription details** (plan, seats, renewal date)  
✅ **Approve major billing changes** (plan upgrades/downgrades)  
✅ **Grant/revoke Brand Admin access**  
✅ **Access all department dashboards** (Growth, Retention, Finance, Operations)  

### What Executive Owner CANNOT Do

❌ **Configure integrations** (Brand Admin responsibility)  
❌ **Manage routine user invitations** (Brand Admin responsibility)  
❌ **Access platform-level Super Admin functions**  
❌ **Modify subscription billing directly** (view-only; changes approved, not executed)  

### Key Principle

Executive Owner sees **decision intelligence**, not just operational dashboards. Every view must answer:
- **What happened?**
- **Why did it happen?**
- **What are the opportunities?**
- **What are the risks?**
- **What happens if assumptions change?**

---

## Pages Required

Executive Owner has **8 primary pages**:

### Page 1: Executive Dashboard (`/dashboard`)
- **Purpose**: Unified business health view with KPIs, alerts, and recommendations
- **URL**: `/dashboard`
- **Components**: KPICardGrid, BusinessHealthPanel, PriorityAlertPanel, RecommendationSummaryPanel, TeamPerformanceRollup

### Page 2: Recommendations (`/recommendations`)
- **Purpose**: View, review, approve/reject, and simulate recommendations
- **URL**: `/recommendations`
- **Components**: RecommendationList, RecommendationCard, RecommendationDetailModal, SimulationLaunchButton

### Page 3: Simulations (`/simulations`)
- **Purpose**: Run strategic simulations and view scenario comparisons
- **URL**: `/simulations`
- **Components**: SimulationForm, SimulationResultsTable, ScenarioComparisonChart

### Page 4: Alerts (`/alerts`)
- **Purpose**: Manage alerts, configure thresholds, and set escalation rules
- **URL**: `/alerts`
- **Components**: AlertList, AlertThresholdConfig, AlertRecipientConfig, EscalationRuleConfig

### Page 5: Growth Dashboard (`/growth`)
- **Purpose**: Channel and campaign performance metrics (drill-down from executive view)
- **URL**: `/growth`
- **Components**: ChannelPerformanceTable, CampaignROASChart, CACPaybackChart

### Page 6: Retention Dashboard (`/retention`)
- **Purpose**: Customer retention, repeat purchase, and cohort analysis
- **URL**: `/retention`
- **Components**: CohortRetentionChart, RepeatPurchaseRateCard, CustomerLifetimeValueChart

### Page 7: Finance Dashboard (`/finance`)
- **Purpose**: Contribution margin, cost drivers, and margin drift analysis
- **URL**: `/finance`
- **Components**: MarginWaterfallChart, CostDriverBreakdownTable, MarginDriftAlerts

### Page 8: Operations Dashboard (`/operations`)
- **Purpose**: Inventory risk, stockout impact, and logistics cost analysis
- **URL**: `/operations`
- **Components**: InventoryRiskTable, StockoutImpactChart, LogisticsCostBreakdown

### Supporting Pages

#### Settings & Configuration (`/settings`)
- **Purpose**: Set KPI targets, configure alert preferences, manage delegations
- **URL**: `/settings`
- **Tabs**: KPI Targets, Alert Configuration, Delegation Rules, Billing (view-only)

---

## API Endpoints Reference

### Base URL
```
https://alpmarklabs-production.up.railway.app
```

### Authentication Header
All endpoints require JWT token:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Permission Requirements
Executive Owner endpoints require `platform_role: "executive_owner"` in JWT token and tenant membership verification.

---

## 1. Executive Dashboard Endpoints

### Endpoint 1.1: Get Executive Overview

**Request:**
```http
GET /tenants/{tenant_id}/executive/overview?period_start=2026-05-01&period_end=2026-05-31
Authorization: Bearer <token>
```

**Query Parameters:**
- `period_start` (date, optional): Start date for analysis (default: 30 days ago)
- `period_end` (date, optional): End date for analysis (default: today)

**Response:** (200 OK)
```json
{
  "total_revenue": 285000.00,
  "gross_profit": 142500.00,
  "contribution_margin": 98750.00,
  "contribution_margin_pct": 34.65,
  "revenue_growth_rate": 12.5,
  "revenue_growth_absolute": 31750.00,
  "blended_roas": 3.8,
  "cac_payback_days": 45.2,
  "repeat_purchase_rate": 28.5,
  "return_rate_pct": 4.2,
  "overall_health_status": "healthy",
  "health_indicators": [
    {
      "area": "growth",
      "status": "healthy",
      "status_message": "Ad spend efficiency is above target with strong ROAS",
      "primary_metric": "Blended ROAS",
      "metric_value": 3.8,
      "metric_target": 3.5,
      "metric_unit": "ratio"
    },
    {
      "area": "retention",
      "status": "warning",
      "status_message": "Repeat purchase rate is below target",
      "primary_metric": "Repeat Purchase Rate",
      "metric_value": 28.5,
      "metric_target": 32.0,
      "metric_unit": "percent"
    },
    {
      "area": "finance",
      "status": "healthy",
      "status_message": "Contribution margin is within target range",
      "primary_metric": "Contribution Margin %",
      "metric_value": 34.65,
      "metric_target": 35.0,
      "metric_unit": "percent"
    },
    {
      "area": "operations",
      "status": "critical",
      "status_message": "2 SKUs at critical stockout risk",
      "primary_metric": "Stockout Risk SKUs",
      "metric_value": 2.0,
      "metric_target": 0.0,
      "metric_unit": "count"
    }
  ],
  "team_performance": [
    {
      "team": "growth",
      "key_metrics": {
        "blended_roas": 3.8,
        "cac_payback_days": 45.2,
        "total_ad_spend": 75000.00
      },
      "trend": "improving",
      "alert_count": 1,
      "recommendation_count": 3
    },
    {
      "team": "retention",
      "key_metrics": {
        "repeat_purchase_rate": 28.5,
        "active_customers": 1850,
        "churn_risk_customers": 120
      },
      "trend": "declining",
      "alert_count": 2,
      "recommendation_count": 2
    },
    {
      "team": "finance",
      "key_metrics": {
        "contribution_margin_pct": 34.65,
        "margin_drift_pct": -0.5,
        "total_cost_drivers": 186250.00
      },
      "trend": "stable",
      "alert_count": 0,
      "recommendation_count": 1
    },
    {
      "team": "operations",
      "key_metrics": {
        "stockout_risk_skus": 2,
        "overstock_skus": 5,
        "total_inventory_value": 425000.00
      },
      "trend": "declining",
      "alert_count": 3,
      "recommendation_count": 4
    }
  ],
  "period_start": "2026-05-01",
  "period_end": "2026-05-31",
  "data_last_synced_at": "2026-06-22T08:30:00Z",
  "currency": "USD"
}
```

**Health Status Values:**
- `"healthy"` - All metrics within target range, no critical issues
- `"warning"` - Some metrics below target, non-critical alerts
- `"critical"` - Major metrics severely off-target, urgent action required

**Team Trend Values:**
- `"improving"` - Key metrics trending positively vs prior period
- `"stable"` - Metrics flat or minor fluctuations
- `"declining"` - Key metrics trending negatively

---

### Endpoint 1.2: Get Executive Trend (Time-Series)

**Request:**
```http
GET /tenants/{tenant_id}/executive/trend?window=NINETY_DAYS
Authorization: Bearer <token>
```

**Query Parameters:**
- `window` (enum, optional): `SEVEN_DAYS`, `THIRTY_DAYS`, `NINETY_DAYS`, `ONE_YEAR`, `CUSTOM` (default: `NINETY_DAYS`)
- `start_date` (date, required if window=CUSTOM): Custom start date
- `end_date` (date, required if window=CUSTOM): Custom end date

**Response:** (200 OK)
```json
{
  "data_points": [
    {
      "snapshot_date": "2026-03-24",
      "revenue_amount": 92000.00,
      "ad_spend_amount": 24500.00,
      "blended_roas": 3.76,
      "contribution_margin_pct": 34.2
    },
    {
      "snapshot_date": "2026-03-25",
      "revenue_amount": 95000.00,
      "ad_spend_amount": 25000.00,
      "blended_roas": 3.80,
      "contribution_margin_pct": 34.5
    }
    // ... 88 more data points for 90-day window
  ],
  "period_start": "2026-03-24",
  "period_end": "2026-06-22",
  "window_label": "Last 90 Days"
}
```

**Purpose:** Used for time-series charts showing KPI trends over time.

---

## 2. Recommendation Endpoints

### Endpoint 2.1: List Recommendations

**Request:**
```http
GET /tenants/{tenant_id}/recommendations?domain=growth&rec_status=new
Authorization: Bearer <token>
```

**Query Parameters:**
- `domain` (string, optional): Filter by domain (`growth`, `retention`, `finance`, `operations`)
- `rec_status` (string, optional): Filter by status (`new`, `reviewed`, `approved`, `rejected`, `implemented_externally`, `outcome_observed`, `expired`, `archived`)
- `gap_flag` (string, optional): Filter by implementation gap (`warning`, `escalated`)
- `has_outcome` (boolean, optional): Show only recommendations with observed outcomes

**Response:** (200 OK)
```json
{
  "items": [
    {
      "id": "rec-uuid-001",
      "tenant_id": "tenant-uuid",
      "rule_id": "growth_channel_reallocation_001",
      "domain": "growth",
      "snapshot_date": "2026-06-21",
      "affected_area": "Meta Ads budget allocation",
      "signal_summary": "Meta Ads ROAS (4.2) is 15% above target while Google Ads ROAS (2.8) is 20% below target",
      "suggested_action": "Reallocate $5,000/month from Google Ads to Meta Ads",
      "estimated_impact": 12500.00,
      "confidence_level": "high",
      "confidence_score": 0.82,
      "data_sources": ["shopify", "meta", "google_ads"],
      "data_freshness_context": "Last synced 2 hours ago",
      "status": "new",
      "priority": 1,
      "review_note": null,
      "created_at": "2026-06-21T09:15:00Z",
      "updated_at": "2026-06-21T09:15:00Z"
    },
    {
      "id": "rec-uuid-002",
      "tenant_id": "tenant-uuid",
      "rule_id": "retention_churn_prevention_001",
      "domain": "retention",
      "snapshot_date": "2026-06-21",
      "affected_area": "High-value customer churn risk",
      "signal_summary": "120 customers at churn risk (no purchase in 45+ days) with avg LTV $450",
      "suggested_action": "Launch re-engagement email campaign with 15% discount offer",
      "estimated_impact": 27000.00,
      "confidence_level": "medium",
      "confidence_score": 0.68,
      "data_sources": ["shopify", "klaviyo"],
      "data_freshness_context": "Last synced 6 hours ago",
      "status": "reviewed",
      "priority": 2,
      "review_note": "Approved by Retention Manager, pending Executive confirmation",
      "created_at": "2026-06-20T14:30:00Z",
      "updated_at": "2026-06-21T10:20:00Z"
    }
  ],
  "total": 2
}
```

**Confidence Levels:**
- `"very_low"` (0.0-0.3): Low signal quality or stale data
- `"low"` (0.3-0.5): Moderate signal with gaps
- `"medium"` (0.5-0.7): Solid signal, some uncertainty
- `"high"` (0.7-0.9): Strong signal, high data quality
- `"very_high"` (0.9-1.0): Very strong signal, excellent data quality

**Status Lifecycle:**
- `new` → `reviewed` → `approved` → `implemented_externally` → `outcome_observed`
- Can be `rejected` at any point
- Can become `expired` if no longer relevant
- Can be `archived` for historical record

---

### Endpoint 2.2: Get Recommendation Detail

**Request:**
```http
GET /tenants/{tenant_id}/recommendations/{recommendation_id}
Authorization: Bearer <token>
```

**Path Parameters:**
- `recommendation_id` (UUID): Recommendation ID

**Response:** (200 OK)
```json
{
  "recommendation": {
    "id": "rec-uuid-001",
    "tenant_id": "tenant-uuid",
    "rule_id": "growth_channel_reallocation_001",
    "domain": "growth",
    "snapshot_date": "2026-06-21",
    "affected_area": "Meta Ads budget allocation",
    "signal_summary": "Meta Ads ROAS (4.2) is 15% above target while Google Ads ROAS (2.8) is 20% below target",
    "suggested_action": "Reallocate $5,000/month from Google Ads to Meta Ads",
    "estimated_impact": 12500.00,
    "confidence_level": "high",
    "confidence_score": 0.82,
    "data_sources": ["shopify", "meta", "google_ads"],
    "data_freshness_context": "Last synced 2 hours ago",
    "status": "new",
    "priority": 1,
    "review_note": null,
    "created_at": "2026-06-21T09:15:00Z",
    "updated_at": "2026-06-21T09:15:00Z"
  },
  "simulations": [
    {
      "id": "sim-uuid-001",
      "created_at": "2026-06-21T11:30:00Z",
      "scenario_name": "Conservative Reallocation",
      "parameters": {
        "meta_budget_increase": 3000,
        "google_budget_decrease": 3000
      },
      "outcomes": {
        "projected_revenue_change": 7500.00,
        "projected_margin_change": 2500.00
      }
    },
    {
      "id": "sim-uuid-002",
      "created_at": "2026-06-21T11:45:00Z",
      "scenario_name": "Aggressive Reallocation",
      "parameters": {
        "meta_budget_increase": 7000,
        "google_budget_decrease": 7000
      },
      "outcomes": {
        "projected_revenue_change": 17500.00,
        "projected_margin_change": 5500.00
      }
    }
  ],
  "simulation_count": 2
}
```

**Purpose:** Show full recommendation with provenance of all simulations launched from it.

---

### Endpoint 2.3: Update Recommendation Status (Approve/Reject)

**Request:**
```http
PATCH /tenants/{tenant_id}/recommendations/{recommendation_id}/status
Authorization: Bearer <token>
Content-Type: application/json

{
  "to_status": "approved",
  "note": "Approved for implementation. Retention Manager to execute by end of week."
}
```

**Request Body:**
- `to_status` (string, required): Target status (`reviewed`, `approved`, `rejected`)
- `note` (string, optional): Approval/rejection reason or instructions

**Response:** (200 OK)
```json
{
  "id": "rec-uuid-001",
  "status": "approved",
  "review_note": "Approved for implementation. Retention Manager to execute by end of week.",
  "updated_at": "2026-06-22T10:15:00Z"
}
```

**Validation Rules:**
- Only `executive_owner` or delegated users can approve/reject
- Cannot approve if confidence_level is `very_low` (system blocks)
- Cannot approve if data_freshness > 7 days (stale data warning shown)
- Approval decision is logged in audit trail

---

### Endpoint 2.4: Launch Simulation from Recommendation

**Request:**
```http
POST /tenants/{tenant_id}/recommendations/{recommendation_id}/simulate
Authorization: Bearer <token>
Content-Type: application/json

{
  "override_parameters": {
    "meta_budget_increase": 6000,
    "google_budget_decrease": 6000
  }
}
```

**Request Body (optional):**
- `override_parameters` (object, optional): Custom parameter adjustments

**Response:** (201 Created)
```json
{
  "simulation_id": "sim-uuid-003",
  "recommendation_id": "rec-uuid-001",
  "scenarios": [
    {
      "scenario_name": "baseline",
      "parameters": {},
      "outcomes": {
        "projected_revenue": 285000.00,
        "projected_margin": 98750.00,
        "projected_roas": 3.8
      }
    },
    {
      "scenario_name": "recommendation",
      "parameters": {
        "meta_budget_increase": 6000,
        "google_budget_decrease": 6000
      },
      "outcomes": {
        "projected_revenue": 300500.00,
        "projected_margin": 103500.00,
        "projected_roas": 4.0
      }
    },
    {
      "scenario_name": "downside",
      "parameters": {
        "meta_roas_decrease": 0.2,
        "meta_budget_increase": 6000,
        "google_budget_decrease": 6000
      },
      "outcomes": {
        "projected_revenue": 292000.00,
        "projected_margin": 100200.00,
        "projected_roas": 3.87
      }
    }
  ],
  "created_at": "2026-06-22T10:30:00Z"
}
```

**Purpose:** Pre-populate simulation with recommendation parameters, run 3 scenarios (baseline, recommendation, downside).

---

## 3. Alert Endpoints

### Endpoint 3.1: Get Alert History

**Request:**
```http
GET /tenants/{tenant_id}/alerts/history?alert_type=stockout_risk
Authorization: Bearer <token>
```

**Query Parameters:**
- `alert_type` (string, optional): Filter by alert type (`stockout_risk`, `margin_drift`, `churn_risk`, `roas_decline`, etc.)
- `event_type` (string, optional): Filter by event (`created`, `acknowledged`, `dismissed`, etc.)

**Response:** (200 OK)
```json
{
  "events": [
    {
      "id": "event-uuid-001",
      "tenant_id": "tenant-uuid",
      "alert_id": "alert-stockout-sku-001",
      "alert_type": "stockout_risk",
      "event_type": "created",
      "actor_user_id": null,
      "event_data": {
        "sku": "SKU-001",
        "product_title": "Classic Tee - Navy",
        "days_to_stockout": 3,
        "estimated_lost_revenue_7d": 15000.00,
        "priority": "critical"
      },
      "created_at": "2026-06-22T06:00:00Z"
    },
    {
      "id": "event-uuid-002",
      "tenant_id": "tenant-uuid",
      "alert_id": "alert-stockout-sku-001",
      "alert_type": "stockout_risk",
      "event_type": "acknowledged",
      "actor_user_id": "user-uuid-ops-manager",
      "event_data": {
        "note": "Reorder placed with supplier, ETA 5 days",
        "acknowledged_by": "operations_manager"
      },
      "created_at": "2026-06-22T09:15:00Z"
    }
  ],
  "total_count": 2
}
```

**Alert Types:**
- `stockout_risk`: Critical/high inventory stockout risk
- `margin_drift`: Contribution margin drift exceeds threshold
- `churn_risk`: High-value customers at churn risk
- `roas_decline`: Channel ROAS below target
- `cac_spike`: Customer acquisition cost above target
- `return_rate_spike`: Return rate exceeds threshold

**Event Types:**
- `created`: Alert triggered
- `acknowledged`: User acknowledged alert
- `dismissed`: User dismissed alert
- `escalation_rule_triggered`: Alert escalated per rule
- `resolved`: Alert condition no longer true

---

### Endpoint 3.2: Acknowledge Alert

**Request:**
```http
POST /tenants/{tenant_id}/alerts/acknowledge
Authorization: Bearer <token>
Content-Type: application/json

{
  "alert_id": "alert-stockout-sku-001",
  "note": "Inventory team notified, reorder in progress"
}
```

**Request Body:**
- `alert_id` (string, required): Alert identifier
- `note` (string, optional): Acknowledgment note

**Response:** (201 Created)
```json
{
  "event_id": "event-uuid-003",
  "alert_id": "alert-stockout-sku-001",
  "event_type": "acknowledged",
  "actor_user_id": "user-uuid-executive",
  "created_at": "2026-06-22T10:45:00Z"
}
```

**Purpose:** Log acknowledgment in immutable audit trail, remove alert from "pending" view.

---

### Endpoint 3.3: Dismiss Alert

**Request:**
```http
POST /tenants/{tenant_id}/alerts/dismiss
Authorization: Bearer <token>
Content-Type: application/json

{
  "alert_id": "alert-margin-drift-meta-001",
  "reason": "Expected seasonal variation, not a concern"
}
```

**Request Body:**
- `alert_id` (string, required): Alert identifier
- `reason` (string, optional): Dismissal reason (recommended for audit)

**Response:** (201 Created)
```json
{
  "event_id": "event-uuid-004",
  "alert_id": "alert-margin-drift-meta-001",
  "event_type": "dismissed",
  "actor_user_id": "user-uuid-executive",
  "created_at": "2026-06-22T11:00:00Z"
}
```

**Purpose:** Permanently dismiss alert (will not re-trigger for same condition).

---

### Endpoint 3.4: Configure Alert Thresholds

**Request:**
```http
POST /tenants/{tenant_id}/alerts/thresholds
Authorization: Bearer <token>
Content-Type: application/json

{
  "alert_type": "margin_drift",
  "metric": "contribution_margin_pct",
  "threshold_value": 2.5,
  "comparison": "below",
  "is_enabled": true
}
```

**Request Body:**
- `alert_type` (string, required): Alert type
- `metric` (string, required): Metric to monitor
- `threshold_value` (float, required): Threshold value
- `comparison` (enum, required): `above`, `below`, `equals`
- `is_enabled` (boolean, required): Enable/disable threshold

**Response:** (201 Created)
```json
{
  "id": "threshold-uuid-001",
  "tenant_id": "tenant-uuid",
  "alert_type": "margin_drift",
  "metric": "contribution_margin_pct",
  "threshold_value": 2.5,
  "comparison": "below",
  "is_enabled": true,
  "created_at": "2026-06-22T11:15:00Z"
}
```

**Purpose:** Set custom alert thresholds (e.g., alert when margin drops below 32.5%).

---

### Endpoint 3.5: Configure Alert Recipients

**Request:**
```http
POST /tenants/{tenant_id}/alerts/recipients
Authorization: Bearer <token>
Content-Type: application/json

{
  "alert_type": "stockout_risk",
  "recipient_user_id": "user-uuid-ops-manager",
  "delivery_channel": "email",
  "is_enabled": true
}
```

**Request Body:**
- `alert_type` (string, required): Alert type
- `recipient_user_id` (UUID, required): User to notify
- `delivery_channel` (enum, required): `email`, `sms`, `in_app`
- `is_enabled` (boolean, required): Enable/disable recipient

**Response:** (201 Created)
```json
{
  "id": "recipient-uuid-001",
  "tenant_id": "tenant-uuid",
  "alert_type": "stockout_risk",
  "recipient_user_id": "user-uuid-ops-manager",
  "recipient_user_email": "ops@one8apparel.com",
  "delivery_channel": "email",
  "is_enabled": true,
  "created_at": "2026-06-22T11:20:00Z"
}
```

**Purpose:** Route specific alert types to specific users via specific channels.

---

### Endpoint 3.6: Create Escalation Rule

**Request:**
```http
POST /tenants/{tenant_id}/alerts/escalation-rules
Authorization: Bearer <token>
Content-Type: application/json

{
  "alert_type": "stockout_risk",
  "priority": "critical",
  "delay_minutes": 60,
  "escalate_to_user_id": "user-uuid-executive"
}
```

**Request Body:**
- `alert_type` (string, required): Alert type
- `priority` (enum, required): `low`, `medium`, `high`, `critical`
- `delay_minutes` (integer, required): Minutes before escalation
- `escalate_to_user_id` (UUID, required): User to escalate to

**Response:** (201 Created)
```json
{
  "id": "escalation-rule-uuid-001",
  "tenant_id": "tenant-uuid",
  "alert_type": "stockout_risk",
  "priority": "critical",
  "delay_minutes": 60,
  "escalate_to_user_id": "user-uuid-executive",
  "escalate_to_user_email": "ceo@one8apparel.com",
  "is_active": true,
  "created_at": "2026-06-22T11:25:00Z"
}
```

**Purpose:** Auto-escalate critical alerts to Executive Owner if not acknowledged within time limit.

---

## 4. Delegation Endpoints

### Endpoint 4.1: Create Delegation Rule

**Request:**
```http
POST /tenants/{tenant_id}/delegation-rules
Authorization: Bearer <token>
Content-Type: application/json

{
  "delegatee_user_id": "user-uuid-growth-manager",
  "domain": "growth",
  "valid_from": "2026-06-22",
  "valid_until": "2026-07-15"
}
```

**Request Body:**
- `delegatee_user_id` (UUID, required): User receiving delegation authority
- `domain` (string, required): Recommendation domain (`growth`, `retention`, `finance`, `operations`)
- `valid_from` (date, required): Start date of delegation period
- `valid_until` (date, required): End date of delegation period (must be >= valid_from)

**Response:** (201 Created)
```json
{
  "id": "delegation-uuid-001",
  "tenant_id": "tenant-uuid",
  "delegator_user_id": "user-uuid-executive",
  "delegatee_user_id": "user-uuid-growth-manager",
  "domain": "growth",
  "valid_from": "2026-06-22",
  "valid_until": "2026-07-15",
  "is_active": true,
  "revoked_at": null,
  "revoked_by_user_id": null,
  "created_at": "2026-06-22T11:30:00Z",
  "updated_at": "2026-06-22T11:30:00Z"
}
```

**Purpose:** Delegate approval authority for growth recommendations to Growth Manager for vacation period.

---

### Endpoint 4.2: List Delegation Rules

**Request:**
```http
GET /tenants/{tenant_id}/delegation-rules
Authorization: Bearer <token>
```

**Response:** (200 OK)
```json
{
  "items": [
    {
      "id": "delegation-uuid-001",
      "tenant_id": "tenant-uuid",
      "delegator_user_id": "user-uuid-executive",
      "delegatee_user_id": "user-uuid-growth-manager",
      "domain": "growth",
      "valid_from": "2026-06-22",
      "valid_until": "2026-07-15",
      "is_active": true,
      "revoked_at": null,
      "revoked_by_user_id": null,
      "created_at": "2026-06-22T11:30:00Z",
      "updated_at": "2026-06-22T11:30:00Z"
    }
  ],
  "total": 1
}
```

---

### Endpoint 4.3: Revoke Delegation Rule

**Request:**
```http
POST /tenants/{tenant_id}/delegation-rules/{delegation_id}/revoke
Authorization: Bearer <token>
```

**Path Parameters:**
- `delegation_id` (UUID): Delegation rule ID

**Response:** (200 OK)
```json
{
  "id": "delegation-uuid-001",
  "is_active": false,
  "revoked_at": "2026-06-22T12:00:00Z",
  "revoked_by_user_id": "user-uuid-executive"
}
```

**Purpose:** Immediately revoke delegation (e.g., Executive Owner returns early from vacation).

---

## 5. Billing & Subscription Endpoints (View-Only)

### Endpoint 5.1: Get Billing Seats

**Request:**
```http
GET /tenants/{tenant_id}/billing-seats
Authorization: Bearer <token>
```

**Response:** (200 OK)
```json
{
  "tenant_id": "tenant-uuid",
  "subscription_plan": "Professional",
  "seat_limit": 10,
  "seats_used": 7,
  "seats_available": 3,
  "next_renewal_date": "2026-07-15",
  "billing_status": "active"
}
```

**Purpose:** View current seat usage and renewal date (read-only for Executive Owner).

---

## 6. Navigation Menu Endpoint

### Endpoint 6.1: Get Navigation Menu

**Request:**
```http
GET /me/navigation?tenant_id={tenant_id}
Authorization: Bearer <token>
```

**Response:** (200 OK)
```json
{
  "user_id": "user-uuid-executive",
  "tenant_id": "tenant-uuid",
  "platform_role": "executive_owner",
  "menu_items": [
    {
      "section": "intelligence",
      "label": "Dashboard",
      "path": "/dashboard",
      "icon": "home",
      "enabled": true,
      "badge_count": null,
      "order": 1
    },
    {
      "section": "intelligence",
      "label": "Recommendations",
      "path": "/recommendations",
      "icon": "lightbulb",
      "enabled": true,
      "badge_count": 10,
      "order": 2
    },
    {
      "section": "intelligence",
      "label": "Simulations",
      "path": "/simulations",
      "icon": "beaker",
      "enabled": true,
      "badge_count": null,
      "order": 3
    },
    {
      "section": "intelligence",
      "label": "Alerts",
      "path": "/alerts",
      "icon": "bell",
      "enabled": true,
      "badge_count": 5,
      "order": 4
    },
    {
      "section": "departments",
      "label": "Growth",
      "path": "/growth",
      "icon": "chart-bar",
      "enabled": true,
      "badge_count": null,
      "order": 5
    },
    {
      "section": "departments",
      "label": "Retention",
      "path": "/retention",
      "icon": "users",
      "enabled": true,
      "badge_count": null,
      "order": 6
    },
    {
      "section": "departments",
      "label": "Finance",
      "path": "/finance",
      "icon": "currency-dollar",
      "enabled": true,
      "badge_count": null,
      "order": 7
    },
    {
      "section": "departments",
      "label": "Operations",
      "path": "/operations",
      "icon": "cube",
      "enabled": true,
      "badge_count": null,
      "order": 8
    },
    {
      "section": "admin",
      "label": "Integrations",
      "path": "/integrations",
      "icon": "link",
      "enabled": true,
      "badge_count": null,
      "order": 9
    },
    {
      "section": "admin",
      "label": "Team",
      "path": "/team",
      "icon": "user-group",
      "enabled": true,
      "badge_count": null,
      "order": 10
    },
    {
      "section": "admin",
      "label": "Billing",
      "path": "/billing",
      "icon": "credit-card",
      "enabled": true,
      "badge_count": null,
      "order": 11
    },
    {
      "section": "admin",
      "label": "Settings",
      "path": "/settings",
      "icon": "cog",
      "enabled": true,
      "badge_count": null,
      "order": 12
    }
  ],
  "unread_alerts": 5,
  "pending_recommendations": 10
}
```

**Purpose:** Dynamically generate role-specific navigation menu with badge counts.

---

## Data Models

### ExecutiveOverviewResponse Model

```typescript
interface ExecutiveOverviewResponse {
  // Primary Financial Metrics
  total_revenue: number;
  gross_profit: number;
  contribution_margin: number;
  contribution_margin_pct: number;

  // Growth Metrics
  revenue_growth_rate: number | null;
  revenue_growth_absolute: number | null;

  // Key Performance Indicators
  blended_roas: number | null;
  cac_payback_days: number | null;
  repeat_purchase_rate: number | null;
  return_rate_pct: number | null;

  // Business Health
  overall_health_status: 'healthy' | 'warning' | 'critical';
  health_indicators: BusinessHealthIndicator[];

  // Cross-Team Rollup
  team_performance: TeamPerformanceSummary[];

  // Metadata
  period_start: string;  // ISO date
  period_end: string;    // ISO date
  data_last_synced_at: string | null;  // ISO timestamp
  currency: string;
}

interface BusinessHealthIndicator {
  area: string;  // 'growth' | 'retention' | 'finance' | 'operations'
  status: 'healthy' | 'warning' | 'critical';
  status_message: string;
  primary_metric: string;
  metric_value: number | null;
  metric_target: number | null;
  metric_unit: string;  // 'percent' | 'dollars' | 'ratio' | 'count'
}

interface TeamPerformanceSummary {
  team: string;  // 'growth' | 'retention' | 'finance' | 'operations'
  key_metrics: Record<string, number | null>;
  trend: 'improving' | 'stable' | 'declining';
  alert_count: number;
  recommendation_count: number;
}
```

---

### Recommendation Model

```typescript
interface Recommendation {
  id: string;  // UUID
  tenant_id: string;  // UUID
  rule_id: string;
  domain: 'growth' | 'retention' | 'finance' | 'operations';
  snapshot_date: string;  // ISO date
  affected_area: string;
  signal_summary: string;
  suggested_action: string;
  estimated_impact: number | null;  // USD
  confidence_level: 'very_low' | 'low' | 'medium' | 'high' | 'very_high';
  confidence_score: number;  // 0.0 - 1.0
  data_sources: string[];  // ['shopify', 'meta', 'google_ads', ...]
  data_freshness_context: string;
  status: 'new' | 'reviewed' | 'approved' | 'rejected' | 
          'implemented_externally' | 'outcome_observed' | 
          'expired' | 'archived';
  priority: number;  // 1 = highest
  review_note: string | null;
  created_at: string;  // ISO timestamp
  updated_at: string;  // ISO timestamp
}

interface RecommendationDetailResponse {
  recommendation: Recommendation;
  simulations: SimulationSummary[];
  simulation_count: number;
}

interface SimulationSummary {
  id: string;
  created_at: string;
  scenario_name: string;
  parameters: Record<string, any>;
  outcomes: Record<string, number>;
}
```

---

### Alert Model

```typescript
interface AlertEvent {
  id: string;  // UUID
  tenant_id: string;  // UUID
  alert_id: string;
  alert_type: string;  // 'stockout_risk' | 'margin_drift' | 'churn_risk' | ...
  event_type: string;  // 'created' | 'acknowledged' | 'dismissed' | ...
  actor_user_id: string | null;  // UUID
  event_data: Record<string, any> | null;
  created_at: string;  // ISO timestamp
}

interface AlertThreshold {
  id: string;  // UUID
  tenant_id: string;  // UUID
  alert_type: string;
  metric: string;
  threshold_value: number;
  comparison: 'above' | 'below' | 'equals';
  is_enabled: boolean;
  created_at: string;
}

interface AlertRecipient {
  id: string;  // UUID
  tenant_id: string;  // UUID
  alert_type: string;
  recipient_user_id: string;  // UUID
  recipient_user_email: string;
  delivery_channel: 'email' | 'sms' | 'in_app';
  is_enabled: boolean;
  created_at: string;
}

interface EscalationRule {
  id: string;  // UUID
  tenant_id: string;  // UUID
  alert_type: string;
  priority: 'low' | 'medium' | 'high' | 'critical';
  delay_minutes: number;
  escalate_to_user_id: string;  // UUID
  escalate_to_user_email: string;
  is_active: boolean;
  created_at: string;
}
```

---

### Delegation Model

```typescript
interface DelegationRule {
  id: string;  // UUID
  tenant_id: string;  // UUID
  delegator_user_id: string | null;  // UUID
  delegatee_user_id: string;  // UUID
  domain: 'growth' | 'retention' | 'finance' | 'operations';
  valid_from: string;  // ISO date
  valid_until: string;  // ISO date
  is_active: boolean;
  revoked_at: string | null;  // ISO timestamp
  revoked_by_user_id: string | null;  // UUID
  created_at: string;  // ISO timestamp
  updated_at: string;  // ISO timestamp
}
```

---

## Component Specifications

### Component 1: KPICardGrid

**Purpose:** Display 7 key KPIs in a responsive grid on Executive Dashboard.

**Location:** `src/components/executive/KPICardGrid.tsx`

**Props:**
```typescript
interface KPICardGridProps {
  overview: ExecutiveOverviewResponse;
  loading?: boolean;
}
```

**Implementation:**

```tsx
import React from 'react';
import KPICard from '../cards/KPICard';
import { ExecutiveOverviewResponse } from '../../api/types';

const KPICardGrid: React.FC<KPICardGridProps> = ({ overview, loading = false }) => {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {[...Array(7)].map((_, i) => (
          <div key={i} className="bg-white rounded-lg shadow-md p-6 h-32 animate-pulse">
            <div className="h-4 bg-neutral-200 rounded w-3/4 mb-3"></div>
            <div className="h-8 bg-neutral-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  const kpis = [
    {
      title: 'Contribution Margin',
      value: overview.contribution_margin_pct,
      unit: '%',
      trend: overview.revenue_growth_rate !== null && overview.revenue_growth_rate > 0 ? 'up' : 'down',
      trendValue: overview.revenue_growth_rate || 0,
      confidence: 'High',
      lastUpdated: overview.data_last_synced_at || 'Unknown'
    },
    {
      title: 'Blended ROAS',
      value: overview.blended_roas || 0,
      unit: 'x',
      trend: 'neutral',
      trendValue: 0,
      confidence: 'High',
      lastUpdated: overview.data_last_synced_at || 'Unknown'
    },
    {
      title: 'CAC Payback',
      value: overview.cac_payback_days || 0,
      unit: 'days',
      trend: 'neutral',
      trendValue: 0,
      confidence: 'Medium',
      lastUpdated: overview.data_last_synced_at || 'Unknown'
    },
    {
      title: 'Repeat Purchase Rate',
      value: overview.repeat_purchase_rate || 0,
      unit: '%',
      trend: 'neutral',
      trendValue: 0,
      confidence: 'High',
      lastUpdated: overview.data_last_synced_at || 'Unknown'
    },
    {
      title: 'Return Rate',
      value: overview.return_rate_pct || 0,
      unit: '%',
      trend: 'neutral',
      trendValue: 0,
      confidence: 'High',
      lastUpdated: overview.data_last_synced_at || 'Unknown'
    },
    {
      title: 'Total Revenue',
      value: overview.total_revenue / 1000,
      unit: 'K',
      trend: overview.revenue_growth_rate !== null && overview.revenue_growth_rate > 0 ? 'up' : 'down',
      trendValue: overview.revenue_growth_rate || 0,
      confidence: 'Very High',
      lastUpdated: overview.data_last_synced_at || 'Unknown'
    },
    {
      title: 'Gross Profit',
      value: overview.gross_profit / 1000,
      unit: 'K',
      trend: 'neutral',
      trendValue: 0,
      confidence: 'High',
      lastUpdated: overview.data_last_synced_at || 'Unknown'
    }
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {kpis.map((kpi, index) => (
        <KPICard
          key={index}
          title={kpi.title}
          value={kpi.value}
          unit={kpi.unit}
          trend={kpi.trend as 'up' | 'down' | 'neutral'}
          trendValue={kpi.trendValue}
          confidence={kpi.confidence}
          lastUpdated={kpi.lastUpdated}
          onClick={() => {
            // Navigate to detailed KPI view
            console.log(`View details for ${kpi.title}`);
          }}
        />
      ))}
    </div>
  );
};

export default KPICardGrid;
```

---

### Component 2: BusinessHealthPanel

**Purpose:** Display 4 functional area health indicators with status badges.

**Location:** `src/components/executive/BusinessHealthPanel.tsx`

**Props:**
```typescript
interface BusinessHealthPanelProps {
  healthIndicators: BusinessHealthIndicator[];
  loading?: boolean;
}
```

**Implementation:**

```tsx
import React from 'react';
import { BusinessHealthIndicator } from '../../api/types';
import { CheckCircleIcon, ExclamationTriangleIcon, XCircleIcon } from '@heroicons/react/24/solid';

const BusinessHealthPanel: React.FC<BusinessHealthPanelProps> = ({ 
  healthIndicators, 
  loading = false 
}) => {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 mb-8">
        <h2 className="text-xl font-bold text-neutral-900 mb-4">Business Health</h2>
        <div className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-16 bg-neutral-100 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircleIcon className="w-6 h-6 text-success-600" />;
      case 'warning':
        return <ExclamationTriangleIcon className="w-6 h-6 text-warning-600" />;
      case 'critical':
        return <XCircleIcon className="w-6 h-6 text-danger-600" />;
      default:
        return null;
    }
  };

  const getStatusBadge = (status: string) => {
    const baseClasses = "inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold";
    switch (status) {
      case 'healthy':
        return `${baseClasses} bg-success-100 text-success-800`;
      case 'warning':
        return `${baseClasses} bg-warning-100 text-warning-800`;
      case 'critical':
        return `${baseClasses} bg-danger-100 text-danger-800`;
      default:
        return `${baseClasses} bg-neutral-100 text-neutral-800`;
    }
  };

  const areaLabels: Record<string, string> = {
    growth: 'Growth & Acquisition',
    retention: 'Retention & CRM',
    finance: 'Finance & Margin',
    operations: 'Operations & Inventory'
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mb-8">
      <h2 className="text-xl font-bold text-neutral-900 mb-4">Business Health</h2>
      <div className="space-y-4">
        {healthIndicators.map((indicator, index) => (
          <div 
            key={index}
            className="flex items-start space-x-4 p-4 bg-neutral-50 rounded-lg hover:bg-neutral-100 transition-colors cursor-pointer"
          >
            {getStatusIcon(indicator.status)}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between mb-1">
                <h3 className="text-base font-semibold text-neutral-900">
                  {areaLabels[indicator.area] || indicator.area}
                </h3>
                <span className={getStatusBadge(indicator.status)}>
                  {indicator.status.toUpperCase()}
                </span>
              </div>
              <p className="text-sm text-neutral-700 mb-2">{indicator.status_message}</p>
              <div className="flex items-center space-x-4 text-xs text-neutral-600">
                <span className="font-medium">{indicator.primary_metric}:</span>
                <span>
                  {indicator.metric_value !== null 
                    ? `${indicator.metric_value.toFixed(2)} ${indicator.metric_unit}` 
                    : 'N/A'}
                </span>
                {indicator.metric_target !== null && (
                  <span className="text-neutral-500">
                    (Target: {indicator.metric_target.toFixed(2)} {indicator.metric_unit})
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default BusinessHealthPanel;
```

---

### Component 3: TeamPerformanceRollup

**Purpose:** Cross-team performance summary with drill-down to department dashboards.

**Location:** `src/components/executive/TeamPerformanceRollup.tsx`

**Props:**
```typescript
interface TeamPerformanceRollupProps {
  teamPerformance: TeamPerformanceSummary[];
  loading?: boolean;
  onTeamClick: (team: string) => void;
}
```

**Implementation:**

```tsx
import React from 'react';
import { TeamPerformanceSummary } from '../../api/types';
import { ArrowTrendingUpIcon, ArrowTrendingDownIcon, MinusIcon } from '@heroicons/react/24/outline';
import { ChevronRightIcon } from '@heroicons/react/20/solid';

const TeamPerformanceRollup: React.FC<TeamPerformanceRollupProps> = ({ 
  teamPerformance, 
  loading = false,
  onTeamClick
}) => {
  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-neutral-900 mb-4">Team Performance</h2>
        <div className="space-y-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-neutral-100 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'improving':
        return <ArrowTrendingUpIcon className="w-5 h-5 text-success-600" />;
      case 'declining':
        return <ArrowTrendingDownIcon className="w-5 h-5 text-danger-600" />;
      case 'stable':
        return <MinusIcon className="w-5 h-5 text-neutral-600" />;
      default:
        return null;
    }
  };

  const getTrendBadge = (trend: string) => {
    const baseClasses = "inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium";
    switch (trend) {
      case 'improving':
        return `${baseClasses} bg-success-100 text-success-800`;
      case 'declining':
        return `${baseClasses} bg-danger-100 text-danger-800`;
      case 'stable':
        return `${baseClasses} bg-neutral-100 text-neutral-800`;
      default:
        return baseClasses;
    }
  };

  const teamLabels: Record<string, string> = {
    growth: 'Growth & Performance',
    retention: 'Retention & CRM',
    finance: 'Finance & Margin',
    operations: 'Operations & Inventory'
  };

  const teamIcons: Record<string, string> = {
    growth: '📈',
    retention: '🔁',
    finance: '💰',
    operations: '📦'
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-bold text-neutral-900 mb-4">Team Performance</h2>
      <div className="space-y-3">
        {teamPerformance.map((team, index) => (
          <div 
            key={index}
            onClick={() => onTeamClick(team.team)}
            className="flex items-center justify-between p-4 bg-neutral-50 rounded-lg hover:bg-neutral-100 transition-colors cursor-pointer group"
          >
            <div className="flex items-start space-x-4 flex-1">
              <div className="text-3xl">{teamIcons[team.team] || '📊'}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-base font-semibold text-neutral-900">
                    {teamLabels[team.team] || team.team}
                  </h3>
                  <span className={getTrendBadge(team.trend)}>
                    {getTrendIcon(team.trend)}
                    {team.trend}
                  </span>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
                  {Object.entries(team.key_metrics).map(([key, value], idx) => (
                    <div key={idx}>
                      <span className="text-neutral-600">{formatMetricLabel(key)}:</span>
                      <span className="ml-1 font-semibold text-neutral-900">
                        {value !== null ? formatMetricValue(key, value) : 'N/A'}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-4 mt-2 text-xs text-neutral-600">
                  {team.alert_count > 0 && (
                    <span className="flex items-center gap-1">
                      <span className="inline-block w-2 h-2 bg-warning-500 rounded-full"></span>
                      {team.alert_count} {team.alert_count === 1 ? 'alert' : 'alerts'}
                    </span>
                  )}
                  {team.recommendation_count > 0 && (
                    <span className="flex items-center gap-1">
                      <span className="inline-block w-2 h-2 bg-primary-500 rounded-full"></span>
                      {team.recommendation_count} {team.recommendation_count === 1 ? 'recommendation' : 'recommendations'}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <ChevronRightIcon className="w-5 h-5 text-neutral-400 group-hover:text-neutral-600 transition-colors" />
          </div>
        ))}
      </div>
    </div>
  );
};

// Helper functions
function formatMetricLabel(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
    .replace(/Pct/g, '%')
    .replace(/Usd/g, 'USD');
}

function formatMetricValue(key: string, value: number): string {
  if (key.includes('pct') || key.includes('rate')) {
    return `${value.toFixed(1)}%`;
  }
  if (key.includes('amount') || key.includes('spend') || key.includes('revenue')) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  if (key.includes('days')) {
    return `${value.toFixed(0)}d`;
  }
  if (key.includes('roas')) {
    return `${value.toFixed(2)}x`;
  }
  return value.toFixed(0);
}

export default TeamPerformanceRollup;
```

---

### Component 4: PriorityAlertPanel

**Purpose:** Display top 5 alerts ranked by business impact.

**Location:** `src/components/executive/PriorityAlertPanel.tsx`

**Props:**
```typescript
interface PriorityAlertPanelProps {
  tenantId: string;
  onViewAllAlerts: () => void;
}
```

**Implementation:**

```tsx
import React, { useEffect, useState } from 'react';
import apiClient from '../../api/client';
import { AlertEvent } from '../../api/types';
import { ExclamationTriangleIcon, BellAlertIcon } from '@heroicons/react/24/outline';

const PriorityAlertPanel: React.FC<PriorityAlertPanelProps> = ({ 
  tenantId, 
  onViewAllAlerts 
}) => {
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAlerts();
  }, [tenantId]);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/tenants/${tenantId}/alerts/history`, {
        params: { event_type: 'created', limit: 5 }
      });
      setAlerts(response.data.events || []);
    } catch (error) {
      console.error('Failed to load alerts:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-neutral-900 mb-4">Priority Alerts</h2>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-neutral-100 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (alerts.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-neutral-900 mb-4">Priority Alerts</h2>
        <div className="text-center py-8">
          <BellAlertIcon className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
          <p className="text-neutral-600">No active alerts</p>
          <p className="text-sm text-neutral-500 mt-1">
            All metrics are within acceptable thresholds
          </p>
        </div>
      </div>
    );
  }

  const getPriorityColor = (alertType: string): string => {
    if (alertType.includes('critical') || alertType.includes('stockout')) return 'danger';
    if (alertType.includes('warning') || alertType.includes('drift')) return 'warning';
    return 'primary';
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-neutral-900">Priority Alerts</h2>
        <button
          onClick={onViewAllAlerts}
          className="text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors"
        >
          View All →
        </button>
      </div>
      <div className="space-y-3">
        {alerts.map((alert) => {
          const priorityColor = getPriorityColor(alert.alert_type);
          return (
            <div 
              key={alert.id}
              className={`flex items-start gap-3 p-4 border-l-4 border-${priorityColor}-500 bg-${priorityColor}-50 rounded-r-lg hover:bg-${priorityColor}-100 transition-colors cursor-pointer`}
            >
              <ExclamationTriangleIcon className={`w-5 h-5 text-${priorityColor}-600 flex-shrink-0 mt-0.5`} />
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold text-neutral-900 mb-1">
                  {formatAlertType(alert.alert_type)}
                </h3>
                <p className="text-xs text-neutral-700 mb-2">
                  {alert.event_data?.priority && (
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium bg-${priorityColor}-200 text-${priorityColor}-900 mr-2`}>
                      {alert.event_data.priority.toUpperCase()}
                    </span>
                  )}
                  {formatAlertMessage(alert)}
                </p>
                <p className="text-xs text-neutral-500">
                  {formatTimeAgo(alert.created_at)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Helper functions
function formatAlertType(alertType: string): string {
  return alertType
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase());
}

function formatAlertMessage(alert: AlertEvent): string {
  const data = alert.event_data || {};
  
  if (alert.alert_type === 'stockout_risk') {
    return `${data.product_title || 'Product'} has ${data.days_to_stockout || 0} days until stockout. Estimated lost revenue: $${(data.estimated_lost_revenue_7d || 0).toLocaleString()}`;
  }
  
  if (alert.alert_type === 'margin_drift') {
    return `Margin drift detected: ${data.drift_pct || 0}% below target`;
  }
  
  return JSON.stringify(data);
}

function formatTimeAgo(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export default PriorityAlertPanel;
```

---

### Component 5: RecommendationSummaryPanel

**Purpose:** Show top 3 pending recommendations on dashboard.

**Location:** `src/components/executive/RecommendationSummaryPanel.tsx`

**Props:**
```typescript
interface RecommendationSummaryPanelProps {
  tenantId: string;
  onViewAllRecommendations: () => void;
}
```

**Implementation:**

```tsx
import React, { useEffect, useState } from 'react';
import apiClient from '../../api/client';
import { Recommendation } from '../../api/types';
import { LightBulbIcon } from '@heroicons/react/24/outline';

const RecommendationSummaryPanel: React.FC<RecommendationSummaryPanelProps> = ({ 
  tenantId, 
  onViewAllRecommendations 
}) => {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRecommendations();
  }, [tenantId]);

  const loadRecommendations = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/tenants/${tenantId}/recommendations`, {
        params: { rec_status: 'new', limit: 3 }
      });
      setRecommendations(response.data.items || []);
    } catch (error) {
      console.error('Failed to load recommendations:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-neutral-900 mb-4">Top Recommendations</h2>
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-neutral-100 rounded animate-pulse"></div>
          ))}
        </div>
      </div>
    );
  }

  if (recommendations.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <h2 className="text-xl font-bold text-neutral-900 mb-4">Top Recommendations</h2>
        <div className="text-center py-8">
          <LightBulbIcon className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
          <p className="text-neutral-600">No new recommendations</p>
          <p className="text-sm text-neutral-500 mt-1">
            AlpMark is analyzing your data. Check back soon.
          </p>
        </div>
      </div>
    );
  }

  const getConfidenceBadge = (level: string) => {
    const baseClasses = "inline-block px-2 py-0.5 rounded text-xs font-semibold";
    switch (level) {
      case 'very_high':
      case 'high':
        return `${baseClasses} bg-success-100 text-success-800`;
      case 'medium':
        return `${baseClasses} bg-warning-100 text-warning-800`;
      case 'low':
      case 'very_low':
        return `${baseClasses} bg-danger-100 text-danger-800`;
      default:
        return `${baseClasses} bg-neutral-100 text-neutral-800`;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-neutral-900">Top Recommendations</h2>
        <button
          onClick={onViewAllRecommendations}
          className="text-sm font-medium text-primary-600 hover:text-primary-700 transition-colors"
        >
          View All →
        </button>
      </div>
      <div className="space-y-4">
        {recommendations.map((rec) => (
          <div 
            key={rec.id}
            className="p-4 border border-neutral-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-all cursor-pointer"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex items-center gap-2">
                <LightBulbIcon className="w-5 h-5 text-warning-500" />
                <span className="text-xs font-medium text-neutral-600 uppercase">
                  {rec.domain}
                </span>
              </div>
              <span className={getConfidenceBadge(rec.confidence_level)}>
                {rec.confidence_level.replace('_', ' ')}
              </span>
            </div>
            <h3 className="text-sm font-semibold text-neutral-900 mb-1">
              {rec.affected_area}
            </h3>
            <p className="text-xs text-neutral-700 mb-2">
              {rec.suggested_action}
            </p>
            <div className="flex items-center justify-between text-xs text-neutral-600">
              <span>
                Estimated impact: 
                <span className="font-semibold text-success-700 ml-1">
                  +${(rec.estimated_impact || 0).toLocaleString()}
                </span>
              </span>
              <span className="text-neutral-500">
                Priority {rec.priority}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default RecommendationSummaryPanel;
```

---

## Page Implementations

### Page 1: Executive Dashboard

**File:** `src/pages/executive/Dashboard.tsx`

**Purpose:** Unified business health view - the Executive Owner's home base.

**Full Implementation:**

```tsx
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import apiClient from '../../api/client';
import { ExecutiveOverviewResponse } from '../../api/types';
import PageContainer from '../../components/layout/PageContainer';
import KPICardGrid from '../../components/executive/KPICardGrid';
import BusinessHealthPanel from '../../components/executive/BusinessHealthPanel';
import TeamPerformanceRollup from '../../components/executive/TeamPerformanceRollup';
import PriorityAlertPanel from '../../components/executive/PriorityAlertPanel';
import RecommendationSummaryPanel from '../../components/executive/RecommendationSummaryPanel';

const ExecutiveDashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [overview, setOverview] = useState<ExecutiveOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });

  useEffect(() => {
    // Default to last 30 days
    const today = new Date();
    const thirtyDaysAgo = new Date(today);
    thirtyDaysAgo.setDate(today.getDate() - 30);
    
    setDateRange({
      start: thirtyDaysAgo.toISOString().split('T')[0],
      end: today.toISOString().split('T')[0]
    });
  }, []);

  useEffect(() => {
    if (user?.tenant_id && dateRange.start && dateRange.end) {
      loadOverview();
    }
  }, [user?.tenant_id, dateRange]);

  const loadOverview = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get(
        `/tenants/${user!.tenant_id}/executive/overview`,
        {
          params: {
            period_start: dateRange.start,
            period_end: dateRange.end
          }
        }
      );
      setOverview(response.data);
    } catch (err: any) {
      console.error('Failed to load executive overview:', err);
      setError(err.response?.data?.detail || 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  const handleTeamClick = (team: string) => {
    navigate(`/${team}`);
  };

  if (error) {
    return (
      <PageContainer title="Executive Dashboard">
        <div className="bg-danger-50 border border-danger-200 rounded-lg p-6 text-center">
          <p className="text-danger-800 font-semibold mb-2">Failed to Load Dashboard</p>
          <p className="text-danger-700 text-sm mb-4">{error}</p>
          <button
            onClick={loadOverview}
            className="px-4 py-2 bg-danger-600 text-white rounded-md hover:bg-danger-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer 
      title="Executive Dashboard"
      actions={
        <div className="flex items-center gap-3">
          <input
            type="date"
            value={dateRange.start}
            onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
            className="px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <span className="text-neutral-500">to</span>
          <input
            type="date"
            value={dateRange.end}
            onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
            className="px-3 py-2 border border-neutral-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            onClick={loadOverview}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors text-sm font-medium"
          >
            Refresh
          </button>
        </div>
      }
    >
      {/* KPI Cards */}
      <KPICardGrid overview={overview!} loading={loading} />

      {/* Business Health */}
      <BusinessHealthPanel 
        healthIndicators={overview?.health_indicators || []} 
        loading={loading} 
      />

      {/* Two-column layout for alerts and recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <PriorityAlertPanel 
          tenantId={user!.tenant_id!}
          onViewAllAlerts={() => navigate('/alerts')}
        />
        <RecommendationSummaryPanel 
          tenantId={user!.tenant_id!}
          onViewAllRecommendations={() => navigate('/recommendations')}
        />
      </div>

      {/* Team Performance Rollup */}
      <TeamPerformanceRollup 
        teamPerformance={overview?.team_performance || []}
        loading={loading}
        onTeamClick={handleTeamClick}
      />

      {/* Data Freshness Indicator */}
      {overview?.data_last_synced_at && (
        <div className="mt-6 p-4 bg-neutral-100 rounded-lg">
          <p className="text-xs text-neutral-600">
            Data last synced: {new Date(overview.data_last_synced_at).toLocaleString()}
          </p>
        </div>
      )}
    </PageContainer>
  );
};

export default ExecutiveDashboard;
```

---

## Navigation & Routing

### Executive Owner Sidebar Navigation

**File:** `src/components/layout/ExecutiveOwnerSidebar.tsx`

```tsx
import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import apiClient from '../../api/client';
import {
  HomeIcon,
  LightBulbIcon,
  BeakerIcon,
  BellAlertIcon,
  ChartBarIcon,
  UsersIcon,
  CurrencyDollarIcon,
  CubeIcon,
  LinkIcon,
  UserGroupIcon,
  CreditCardIcon,
  Cog6ToothIcon
} from '@heroicons/react/24/outline';

interface NavigationItem {
  section: string;
  label: string;
  path: string;
  icon: string;
  enabled: boolean;
  badge_count: number | null;
  order: number;
}

const ExecutiveOwnerSidebar: React.FC = () => {
  const { user } = useAuth();
  const [navItems, setNavItems] = useState<NavigationItem[]>([]);

  useEffect(() => {
    if (user?.tenant_id) {
      loadNavigation();
    }
  }, [user?.tenant_id]);

  const loadNavigation = async () => {
    try {
      const response = await apiClient.get('/me/navigation', {
        params: { tenant_id: user!.tenant_id }
      });
      setNavItems(response.data.menu_items || []);
    } catch (error) {
      console.error('Failed to load navigation:', error);
    }
  };

  const getIcon = (iconName: string) => {
    const iconMap: Record<string, any> = {
      home: HomeIcon,
      lightbulb: LightBulbIcon,
      beaker: BeakerIcon,
      bell: BellAlertIcon,
      'chart-bar': ChartBarIcon,
      users: UsersIcon,
      'currency-dollar': CurrencyDollarIcon,
      cube: CubeIcon,
      link: LinkIcon,
      'user-group': UserGroupIcon,
      'credit-card': CreditCardIcon,
      cog: Cog6ToothIcon
    };
    return iconMap[iconName] || HomeIcon;
  };

  const groupedItems = navItems.reduce((acc, item) => {
    if (!acc[item.section]) {
      acc[item.section] = [];
    }
    acc[item.section].push(item);
    return acc;
  }, {} as Record<string, NavigationItem[]>);

  const sectionTitles: Record<string, string> = {
    intelligence: 'Intelligence',
    departments: 'Departments',
    admin: 'Administration'
  };

  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-white shadow-lg border-r border-neutral-200 overflow-y-auto">
      {/* Logo */}
      <div className="p-6 border-b border-neutral-200">
        <h1 className="text-2xl font-bold text-primary-600">AlpMark</h1>
        <p className="text-xs text-neutral-600 mt-1">Intelligence Platform</p>
      </div>

      {/* Navigation */}
      <nav className="p-4 space-y-6">
        {Object.entries(groupedItems).map(([section, items]) => (
          <div key={section}>
            <h2 className="px-3 mb-2 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
              {sectionTitles[section] || section}
            </h2>
            <div className="space-y-1">
              {items
                .sort((a, b) => a.order - b.order)
                .map((item) => {
                  if (!item.enabled) return null;
                  
                  const Icon = getIcon(item.icon);
                  
                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={({ isActive }) =>
                        `flex items-center justify-between px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                          isActive
                            ? 'bg-primary-50 text-primary-700 border-l-4 border-primary-600'
                            : 'text-neutral-700 hover:bg-neutral-100 hover:text-neutral-900'
                        }`
                      }
                    >
                      <div className="flex items-center gap-3">
                        <Icon className="w-5 h-5" />
                        <span>{item.label}</span>
                      </div>
                      {item.badge_count !== null && item.badge_count > 0 && (
                        <span className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-danger-500 rounded-full">
                          {item.badge_count > 99 ? '99+' : item.badge_count}
                        </span>
                      )}
                    </NavLink>
                  );
                })}
            </div>
          </div>
        ))}
      </nav>

      {/* User Info */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-neutral-200 bg-neutral-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-600 rounded-full flex items-center justify-center text-white font-bold">
            {user?.full_name?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-neutral-900 truncate">
              {user?.full_name || 'User'}
            </p>
            <p className="text-xs text-neutral-600 truncate">
              {user?.email}
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default ExecutiveOwnerSidebar;
```

---

## Step-by-Step Build Instructions

### Step 1: Install Additional Dependencies

```bash
cd alpmark-frontend

# Install date utilities for trend charts
npm install date-fns

# Install chart library
npm install recharts

# Install additional icons
npm install @heroicons/react
```

### Step 2: Create API Types

**File:** `src/api/types.ts`

Add Executive Owner types:

```typescript
// Executive Dashboard Types
export interface ExecutiveOverviewResponse {
  total_revenue: number;
  gross_profit: number;
  contribution_margin: number;
  contribution_margin_pct: number;
  revenue_growth_rate: number | null;
  revenue_growth_absolute: number | null;
  blended_roas: number | null;
  cac_payback_days: number | null;
  repeat_purchase_rate: number | null;
  return_rate_pct: number | null;
  overall_health_status: 'healthy' | 'warning' | 'critical';
  health_indicators: BusinessHealthIndicator[];
  team_performance: TeamPerformanceSummary[];
  period_start: string;
  period_end: string;
  data_last_synced_at: string | null;
  currency: string;
}

export interface BusinessHealthIndicator {
  area: string;
  status: 'healthy' | 'warning' | 'critical';
  status_message: string;
  primary_metric: string;
  metric_value: number | null;
  metric_target: number | null;
  metric_unit: string;
}

export interface TeamPerformanceSummary {
  team: string;
  key_metrics: Record<string, number | null>;
  trend: 'improving' | 'stable' | 'declining';
  alert_count: number;
  recommendation_count: number;
}

// Recommendation Types
export interface Recommendation {
  id: string;
  tenant_id: string;
  rule_id: string;
  domain: 'growth' | 'retention' | 'finance' | 'operations';
  snapshot_date: string;
  affected_area: string;
  signal_summary: string;
  suggested_action: string;
  estimated_impact: number | null;
  confidence_level: 'very_low' | 'low' | 'medium' | 'high' | 'very_high';
  confidence_score: number;
  data_sources: string[];
  data_freshness_context: string;
  status: string;
  priority: number;
  review_note: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecommendationListResponse {
  items: Recommendation[];
  total: number;
}

// Alert Types
export interface AlertEvent {
  id: string;
  tenant_id: string;
  alert_id: string;
  alert_type: string;
  event_type: string;
  actor_user_id: string | null;
  event_data: Record<string, any> | null;
  created_at: string;
}

export interface AlertEventListResponse {
  events: AlertEvent[];
  total_count: number;
}

// Delegation Types
export interface DelegationRule {
  id: string;
  tenant_id: string;
  delegator_user_id: string | null;
  delegatee_user_id: string;
  domain: string;
  valid_from: string;
  valid_until: string;
  is_active: boolean;
  revoked_at: string | null;
  revoked_by_user_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface DelegationRuleListResponse {
  items: DelegationRule[];
  total: number;
}
```

### Step 3: Build Components (Order)

1. ✅ `KPICardGrid.tsx` (uses existing KPICard component from Super Admin guide)
2. ✅ `BusinessHealthPanel.tsx`
3. ✅ `TeamPerformanceRollup.tsx`
4. ✅ `PriorityAlertPanel.tsx`
5. ✅ `RecommendationSummaryPanel.tsx`

### Step 4: Build Pages (Order)

1. ✅ `Dashboard.tsx` (Executive Dashboard - main entry point)
2. `Recommendations.tsx` (full recommendations list with filters)
3. `Simulations.tsx` (simulation runner and results)
4. `Alerts.tsx` (alert management and configuration)
5. `Settings.tsx` (KPI targets, alert config, delegations)

### Step 5: Update Routing

**File:** `src/App.tsx`

Add Executive Owner routes:

```tsx
import ExecutiveDashboard from './pages/executive/Dashboard';
import Recommendations from './pages/executive/Recommendations';
import Simulations from './pages/executive/Simulations';
import Alerts from './pages/executive/Alerts';
import Settings from './pages/executive/Settings';

// In Routes section:
<Route
  path="/dashboard"
  element={
    <ProtectedRoute allowedRoles={['executive_owner']}>
      <ExecutiveDashboard />
    </ProtectedRoute>
  }
/>
<Route
  path="/recommendations"
  element={
    <ProtectedRoute allowedRoles={['executive_owner', 'growth_performance_manager', 'retention_crm_manager', 'finance_controller', 'operations_manager']}>
      <Recommendations />
    </ProtectedRoute>
  }
/>
<Route
  path="/simulations"
  element={
    <ProtectedRoute allowedRoles={['executive_owner']}>
      <Simulations />
    </ProtectedRoute>
  }
/>
<Route
  path="/alerts"
  element={
    <ProtectedRoute allowedRoles={['executive_owner', 'growth_performance_manager', 'retention_crm_manager', 'finance_controller', 'operations_manager']}>
      <Alerts />
    </ProtectedRoute>
  }
/>
<Route
  path="/settings"
  element={
    <ProtectedRoute allowedRoles={['executive_owner']}>
      <Settings />
    </ProtectedRoute>
  }
/>
```

### Step 6: Environment Variables

**File:** `.env`

```
VITE_API_URL=https://alpmark-production.up.railway.app
```

### Step 7: Test with Real Data

**Login as Executive Owner:**
- Tenant: `one8` (from seed_one8.py)
- Email: Use Executive Owner email from database
- Password: Set during onboarding

**Test Flow:**
1. Login → should redirect to `/dashboard`
2. Verify KPI cards load with real data
3. Check business health indicators show correct status
4. Verify team performance rollup displays all 4 teams
5. Test alert panel shows active alerts
6. Test recommendation panel shows pending recommendations
7. Click team names → should navigate to department dashboards
8. Test date range filter and refresh button

---

## Summary

This guide provides **everything** needed to build the Executive Owner frontend:

✅ **8 primary pages** with dashboard, recommendations, simulations, alerts, department views, and settings  
✅ **15+ API endpoints** with exact request/response formats  
✅ **10+ data models** with complete TypeScript interfaces  
✅ **5 core components** with full implementations  
✅ **Dynamic navigation** with role-based menu and badge counts  
✅ **Business intelligence UI** with KPIs, health indicators, team rollup  
✅ **Recommendation approval workflow** with delegation support  
✅ **Alert management** with thresholds, recipients, and escalation rules  
✅ **Step-by-step build instructions**  

**Total Implementation Time:** ~12-16 hours for experienced React developer

**Key Differences from Super Admin:**
- **Intelligence-focused**: Executive Owner sees business insights, not platform operations
- **Cross-team visibility**: Can view all department dashboards
- **Approval authority**: Can approve/reject recommendations
- **Strategic simulations**: Can run what-if scenarios
- **Delegation**: Can delegate approval authority during vacation/busy periods
- **Alert ownership**: Can configure thresholds and routing for entire tenant

**Next Persona:** Brand Admin (workspace administration without business analytics)

---

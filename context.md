
# AlpMark Intelligence Platform - Working Document

Status: In progress a(step-by-step, approval-gated)
Current progress: Step 11 COMPLETE - Tech Spec saved. Next: Step 12 Phase Plan
Date started: 2026-04-28

## Agreed Process (14 Steps)
1. Problem Statement
2. Business Outcomes and Success Metrics
3. Personas
4. User Journeys
5. Epics
6. Functional Requirements
7. User Stories
8. NFRs
9. Scope and Priority
10. Solution Approach and Trade-offs
11. Tech Spec
12. Phase Plan
13. Implementation and Verification
14. Launch Governance

## Cross-Cutting Rules (Applies to all Personas and Future Steps)

1) Action boundary
- AlpMark is decision-intelligence only: recommend, simulate, approve-log, and track outcomes.
- AlpMark does not execute external business actions in ad/e-commerce platforms.

2) Recommendation lifecycle (minimum statuses)
- New
- Reviewed
- Approved (in AlpMark)
- Rejected
- Implemented externally
- Outcome observed

3) External action verification
- Implementation is inferred from synced source data (for example status/spend changes), not executed by AlpMark.
- Inferred status must show source and timestamp.

4) Data freshness and trust signals
- Every connected source must expose last synced timestamp.
- Recommendations and simulations must show confidence level and data recency context.

5) Approval semantics
- In-app approvals are governance records only; they do not trigger external execution.

6) Simulation governance
- Simulation output must include expected upside and downside/risk view.

7) Outcome evaluation window
- Recommendation impact is evaluated over a defined window (to be finalized in later step).

8) Missing/noisy data behavior
- Low-confidence or stale-data conditions must be surfaced before showing high-impact recommendations.


## Step 1 - Problem Statement (Approved)
Target segment:
- E-commerce D2C brands selling physical products.

Primary problem:
- Data is fragmented across tools and channels, so teams do not have a single trusted view of business performance.
- This causes slow and inconsistent decisions, manual analysis overhead, and avoidable margin/profit leakage.

AlpMark value promise:
- Unify key business data.
- Provide actionable insights and recommendations.
- Enable simulation-based decisioning before making real-world changes.
- Improve decision speed and profitability while reducing inefficiency and manual work.

Approved problem statement:
- E-commerce D2C brands operate across many tools and channels, but lack a unified and trusted view of business performance. This fragmentation causes slow, inconsistent, and often suboptimal decisions, leading to avoidable profit leakage, operational inefficiency, and high manual analysis effort. AlpMark Intelligence Platform solves this by unifying key business data, surfacing actionable insights and recommendations, and enabling simulation-based decisioning to improve profitability and decision speed.

Scope boundary for now:
- In scope: E-commerce D2C physical-product brands.
- Out of scope at this stage: SaaS/digital-only business models and enterprise custom workflows.

## Step 2 - Business Outcomes and Success Metrics (Approved)

Business outcome:
- Primary objective: Improve profitability for E-commerce D2C physical-product brands.
- Secondary objectives:
  - Improve decision speed.
  - Reduce inefficiency and manual analysis effort.
  - Reduce avoidable losses from poor spend/channel decisions.

Success KPI set:
- Contribution Margin %
- CAC Payback Period
- Blended ROAS
- Return Rate %
- Repeat Purchase Rate
- CAC by Channel
- Time to Insight

Baseline policy:
- Baseline for each KPI is TBD at onboarding.
- Baseline is established from the first connected data snapshot per brand.

6-month target ranges:
- Contribution Margin %: improve by +3% to +8%
- CAC Payback Period: reduce by -15% to -20%
- Blended ROAS: improve by +10% to +15%
- Return Rate %: reduce by -10%
- Repeat Purchase Rate: improve by +8% to +12%
- CAC by Channel: identify and reallocate from bottom 1-2 inefficient channels
- Time to Insight: reduce to under 1 hour for standard decision workflows

Guardrails (final 7):
- Do not let improving one metric harm another metric.
- Do not improve ROAS by cuts that reduce repeat purchase health.
- Do not improve margin via actions that materially worsen return rate.thi
- Recommendations must show cross-metric impact, not single-metric optimization.
- Do not reduce CAC in ways that drop qualified customer volume below acceptable threshold.
- Do not surface recommendations without minimum confidence; show confidence level.
- Simulator outputs must always include downside/risk scenarios, not just upside.


## Current Step
- Step 3: Personas (Approved - all 8 personas complete).
- Step 4: User Journeys (in progress).
- Completed in Step 4: JRN-01 Tenant Provisioning, JRN-02 Brand Admin Onboarding, JRN-03 Executive Owner Strategic Review, JRN-04 Growth and Performance Manager, JRN-05 Retention and CRM Manager, JRN-06 Finance Controller, JRN-07 Operations and Inventory Manager, JRN-08 AlpMark Support/Admin Operator.
- Step 4 COMPLETE. Step 5 COMPLETE. Step 6 COMPLETE - EPC-01 to EPC-11 saved (FR-001 to FR-126). Step 7 COMPLETE - US-001 to US-126 saved. Step 8 COMPLETE - NFR-001 to NFR-024 saved. Next: Step 9 Scope and Priority.
- **T-068 COMPLETE**: Historical restatement engine, 268/268 tests passing ✓. **T-069 COMPLETE**: Warehouse-level inventory views (FR-063–065), 276/276 tests passing ✓. Location model with metadata, multi-warehouse aggregate views (Phase 1), stockout impact estimation, logistics cost breakdown. All code quality gates passed. **T-070 COMPLETE**: Retention acquisition context API (FR-043), 284/284 tests passing ✓ (8 new tests). AcquisitionCohort model, migration, 3 schemas, GET endpoint with date/channel filtering, data freshness detection, audit logging, timezone-aware datetime handling. All code quality gates passed (Ruff, mypy, pytest). **T-071 COMPLETE**: Custom Segment Definition APIs (FR-044), 292/292 tests passing ✓ (8 new tests). CustomSegment ORM model with tenant/name uniqueness, Alembic migration, 4 Pydantic schemas (Create, Update, Response, ListResponse), 5 REST endpoints (POST/GET/PUT/DELETE + list) with OperationsManagerDep auth, cross-tenant isolation, audit logging. All code quality gates passed (Ruff 0 violations, pytest 292/292).

## Step 3 - Personas (In progress)

### PER-01 Executive Owner (Approved)
Purpose:
- Strategic decision-maker accountable for business profitability and direction; needs trusted executive-level intelligence rather than operational tooling.

What they need to see:
- Unified executive business health view: revenue, profit, contribution margin, trend direction.
- Step-2 KPI summary and drift indicators.
- Prioritized risk/opportunity alerts and expected impact.
- Recommendation summary with projected profitability impact.
- Cross-team performance roll-up (growth, retention, operations, finance) with drill-down.
- Strategic simulation outcomes for major decisions.
- Billing and subscription visibility (plan, renewal, usage, invoice/payment status).

What they can do:
- View all brand-level dashboards, insights, and reports.
- Run and review strategic simulations.
- Approve or dismiss strategic recommendations.
- Set/update business targets and alert preferences.
- Grant/revoke Brand Admin access.
- Approve major billing/subscription changes.

What they must not control:
- Day-to-day integration setup or technical connector configuration.
- Granular role assignment below Brand Admin level.
- Low-level API/system configuration.
- Routine billing operations execution.

PER-01 operational refinements (agreed):
- Delegation rule must exist for executive approvals.
- Approval thresholds must define what counts as major billing changes.
- Alert preferences must be configurable for executive signal/noise control.

### PER-02 Growth and Performance Manager (Approved)
Purpose:
- Owns acquisition and media efficiency decisions; uses AlpMark to make faster, more profitable spend decisions.

What they need to see:
- Channel/campaign efficiency view: spend, CAC, ROAS, payback, trend.
- Blended and channel-level profitability impact.
- Budget reallocation recommendations with expected KPI impact.
- Early warnings for declining performance and inefficient spend pockets.
- Simulation outcomes for spend/channel-mix scenarios.
- Recommendation status tracking (recommended, approved, implemented externally, observed impact).

What they can do:
- Analyze channel/campaign performance inside AlpMark.
- Run and compare simulations.
- Approve/reject/flag recommendations inside AlpMark (decision record only).
- Create annotations and save analysis views.
- Configure performance alerts and thresholds.
- Share/export decision summaries for executive review.

What they must not control:
- Any direct execution in external ad platforms (no pause/scale/budget push actions from AlpMark).
- User/role management and tenant administration.
- Billing/subscription operations.
- Finance model ownership (cost-accounting definitions).
- Global platform/system settings.

### Next persona
- PER-04 Finance Controller (ready).

### PER-03 Retention and CRM Manager (Approved)
Purpose:
- Owns customer retention, repeat purchase growth, and lifecycle engagement. Uses AlpMark to identify where revenue is being lost after first purchase and what actions should improve repeat behavior and customer value.

What they need to see:
- Repeat purchase rate trends and cohort retention curves (per time-period cohort with side-by-side cohort comparison).
- Customer lifecycle funnel signals (first order to second order to repeat cadence).
- Segment-level performance: new vs returning, high-value vs at-risk cohorts, and segment-level contribution margin.
- Churn-risk and drop-off indicators by segment and time window (0-30, 30-60, 60-90 days post first purchase).
- Return/refund behavior as a retention signal (not operational/logistics view; that belongs to PER-05).
- Read-only visibility into acquisition metrics from growth (channel, CAC, new customer quality) to understand what retention is working with.
- Recommendation feed focused on retention levers and expected margin impact.
- Simulation outputs for retention scenarios (timing, intensity, segment assumptions) with upside and downside view.
- Outcome tracking for implemented recommendations (inferred from synced data post external execution).

What they can do:
- Analyze retention and cohort performance inside AlpMark.
- Run and compare retention simulations with own assumption inputs (response rates, timing, segment scope).
- Approve/reject/flag retention recommendations inside AlpMark (governance record only).
- Define and save retention alert thresholds (for example: alert when repeat rate drops below X% for any cohort).
- Build and save custom segment views for repeated use.
- Annotate lifecycle events for context (sale periods, catalog changes, policy changes).
- Export and share retention decision summaries with Executive Owner, Growth, and Finance stakeholders.

What they must not control:
- Direct execution in CRM or marketing automation tools from AlpMark.
- User/role administration and tenant governance.
- Billing/subscription operations.
- Finance model ownership (cost-accounting and margin definition controls).
- Global platform/system settings.
- Final executive approval on major strategic or budget commitments.

PER-03 refinements (agreed):
- Retention manager has read-only visibility into acquisition metrics to understand incoming customer quality.
- Cohort comparison across time periods must be an explicit capability.
- Returns/refund data is consumed as a retention signal only, not an ops view.
- Retention simulation assumption inputs (response rate, timing, intensity) are owned and set by the retention manager.


### PER-04 Finance Controller (Approved)
Purpose:
- Owns financial accuracy and profitability governance. Ensures AlpMark metrics, insights, and simulations reflect true business economics with trusted, clearly sourced cost inputs.

Cost Input Sourcing Rule (agreed):
- AlpMark uses a two-tier model for cost inputs:
  1. Where a connected data source exists (Shopify COGS, actual return data, connected shipping platform), AlpMark pulls real data automatically. No manual input required.
  2. Where no connected source exists (e.g., 3PL invoices not in any API, return processing/restocking costs, manually tracked COGS), Finance Controller provides manual inputs.
- All metrics built on manual inputs are clearly labelled and carry a lower confidence indicator than metrics built on live synced data.
- Finance Controller's role is to validate synced data, provide manual inputs where gaps exist, and maintain the accuracy of cost inputs over time — not to assume values that the system should know.

What they need to see:
- Contribution margin breakdown by channel, product, and order type.
- Cost driver visibility for COGS, shipping, returns, discounts, and ad spend impact on margin — with source label (synced vs manual) for each input.
- Period-level P&L-aligned profitability views (weekly/monthly).
- Margin trend vs expected values, with drift alerts when actual performance deviates beyond threshold.
- Financial impact previews for recommendations before decision approval.
- Simulation outcomes from a finance lens (margin, payback, downside risk).
- Confidence and data freshness indicators on all financial outputs, with manual vs synced source clearly distinguished.
- Historical cost input change log and impacted metric deltas.

What they can do:
- View and validate cost inputs pulled from connected sources.
- Provide and update manual cost inputs where no connected source exists (e.g., return processing cost, 3PL rate).
- Configure shipping cost bands, return cost rates, discount policy inputs, and similar financial parameters not covered by connected sources.
- Set drift thresholds and alert rules for margin and cost variance.
- Configure threshold profiles by channel/category (not only one global threshold).
- Run simulations using finance-side cost inputs.
- Approve, reject, or flag cost inputs used by recommendations/simulations.
- Apply explicit approval lock for high-impact cost input changes before they affect recommendations/simulations.
- Version cost inputs with effective dates (immediate or scheduled).
- Add variance reason tags (for example: discount spike, shipping increase, return surge).
- Export finance summaries and reporting views for leadership/governance use.
- Restate historical periods under prior vs new cost inputs for audit comparison.

What they must not control:
- External system execution actions from AlpMark.
- User/role administration and tenant-level access governance.
- Billing/subscription operational controls.
- Global platform/system configuration.
- Non-financial workflow administration unrelated to profitability governance.

### PER-05 Operations and Inventory Manager (Approved)
Purpose:
- Owns operational efficiency that directly impacts profitability: inventory health, fulfillment performance, returns burden, and stock availability. Uses AlpMark to identify operational drivers of margin leakage and evaluate improvement scenarios before external action is taken.

What they need to see:
- Inventory health by SKU/category: in-stock, low-stock, stockout risk, overstock risk.
- Fulfillment and logistics cost impact on contribution margin.
- Return/refund operational patterns: return rate, return cost burden, top return-driving SKUs/categories.
- Stockout impact estimates on lost revenue and repeat purchase risk.
- Slow-moving inventory signals and discount pressure implications.
- Operational anomaly alerts (sudden return spike, shipping-cost spike, stockout cluster).
- Recommendation feed focused on operational levers with expected margin impact.
- Simulation outputs for ops scenarios (inventory policy, reorder timing, return-rate change assumptions) with upside/downside view.
- Outcome tracking for externally implemented operational decisions via synced data.

What they can do:
- Analyze inventory, returns, and fulfillment trends inside AlpMark.
- Run and compare operational simulations using assumption inputs (reorder timing, return-cost assumptions, shipping-cost changes).
- Approve/reject/flag operational recommendations inside AlpMark (governance record only).
- Configure operational alert thresholds and save recurring operational views.
- Add operational context annotations (supplier delay, warehouse issue, policy change).
- Export ops impact summaries for leadership decision reviews.
- Track recommendation lifecycle and observed outcome after external implementation.

What they must not control:
- Direct execution in ERP/WMS/3PL/e-commerce systems from AlpMark.
- User/role administration and tenant access governance.
- Billing/subscription operational controls.
- Global platform/system configuration.
- Non-operational workflow administration unrelated to inventory/operations governance.

PER-05 refinements (agreed):
- Multi-warehouse view support for brands operating multiple fulfillment nodes.
- Service-level context in alerts (for example, stockout risk with expected days-to-stockout).
- Explicit separation of operational returns view vs customer-retention analytics view.
- External-action evidence markers (what changed, source, sync timestamp) for post-decision tracking.

### Next persona
- PER-07 AlpMark Super Admin (ready).

### PER-06 Brand Admin (Approved)
Purpose:
- Manages the operational health of the brand's AlpMark account. Responsible for user access, role assignments, integration connections, and billing operations. Ensures the platform is correctly configured, connected, and governed so all other personas can function effectively.

What they need to see:
- Full list of brand users, their assigned roles, and access status.
- Integration connection health: connected sources, sync status, last synced timestamp, and error alerts.
- Pending user invitations and access requests awaiting approval.
- Billing and subscription details: current plan, seat usage, renewal date, invoices, payment status.
- Audit log of access changes, role modifications, and integration events within the brand account.
- Platform usage summary (who is using what, last active timestamps per user).
- Onboarding completion tracker showing setup progress across users, integrations, and configurations.

What they can do:
- Invite new users to the brand account by email.
- Assign and modify roles for brand users (all roles except Executive Owner).
- Approve or reject pending access requests.
- Deactivate or remove user access immediately.
- Connect, configure, and manage data source integrations (Shopify, ad platforms, etc.).
- Rotate, revoke, and re-authenticate integration credentials (OAuth tokens, API keys) when they expire or break.
- Monitor integration sync health and trigger manual re-syncs where available.
- Receive and action integration failure alerts as primary resolution owner.
- Execute routine billing operations (update payment method, manage seats, download invoices).
- Request plan upgrades or downgrades for Executive Owner approval.
- Configure platform notification routing (who receives which alert type).
- View and export audit logs for governance and compliance purposes.

What they must not control:
- Business analytics, dashboards, insights, or recommendations (no analytical access by default).
- Cost-model assumptions and financial parameters.
- Strategic recommendation approvals or simulation decisions.
- AlpMark platform-level settings outside their tenant.
- Executive Owner role assignment (only Executive Owner can grant/revoke Brand Admin access).
- Plan cancellation (Executive Owner only).

PER-06 refinements (agreed):
- Integration credential management: Brand Admin can rotate, revoke, and re-authenticate OAuth/API credentials.
- Integration failure escalation ownership: Brand Admin is primary alert recipient and resolution owner for sync/connector failures.
- Onboarding checklist ownership: Brand Admin owns completion of initial setup (sources, users, roles).
- Notification routing configuration: Brand Admin configures which persona receives which alert type.

### PER-07 AlpMark Super Admin (Approved)
Purpose:
- Platform-level operator for the AlpMark SaaS product. Owns tenant lifecycle, global configuration, platform health, and billing governance across all customer accounts. Has the highest level of access in the system and every action is strictly audit-logged.

What they need to see:
- Full tenant directory: all customer accounts, their status, plan, seat count, and activity.
- Platform health and system status across all tenants.
- Integration health at platform level: connector errors, sync failures, data ingestion issues across tenants.
- Billing and subscription status for all tenants: plan, renewal, payment status, overdue accounts.
- Global audit log of all platform-level actions and tenant-level escalations.
- Usage and adoption metrics across tenants (aggregate, not individual business data).
- Support escalation queue and open incidents.

What they can do:
- Create, configure, suspend, and delete tenant accounts.
- Assign and modify AlpMark-side operator roles (Super Admin, Support Operator).
- Manage platform-level integration configurations and connector infrastructure.
- Override tenant-level settings in emergency or escalation scenarios only.
- Manage billing and subscription lifecycle for all tenants (plan changes, cancellations, renewals).
- Access tenant environments for support and incident resolution (with full audit trail).
- Configure global platform settings, feature flags, and rollout controls.
- Trigger platform-wide maintenance, data integrity checks, and incident responses.
- View and export global audit logs.

What they must not control:
- Individual tenant business data unless explicitly required for incident resolution and fully logged.
- Customer business decisions, recommendations, or simulations.
- Direct manipulation of tenant analytics outputs outside of incident scope.

PER-07 refinements (agreed):
- All Super Admin access to tenant environments must be time-limited, purpose-logged, with operator identity and timestamp.
- Destructive actions (tenant deletion, plan cancellation) require a two-step confirmation.

### Next persona
- PER-08 AlpMark Support/Admin Operator (ready).

### PER-08 AlpMark Support/Admin Operator (Approved)
Purpose:
- Handles customer support, onboarding assistance, and operational incidents on behalf of AlpMark. Works within tenant environments only when needed for resolution, always under audit. Does not have platform-level governance authority and cannot make destructive or billing-level changes.

What they need to see:
- Assigned support tickets and open incidents.
- Tenant account status: plan, seat count, integration health, sync errors.
- Tenant user list and role assignments (read-only, for support context).
- Integration and connector diagnostic information for troubleshooting.
- Audit log of their own actions within tenant environments.
- Onboarding progress tracker for brands they are assisting.

What they can do:
- View tenant environments for support and troubleshooting purposes (read-only by default).
- Assist with integration setup and connector configuration during onboarding.
- Trigger manual data re-syncs to resolve ingestion issues.
- Escalate unresolved incidents to AlpMark Super Admin.
- Add internal support notes and resolution logs to tickets.
- Guide Brand Admins through platform setup and configuration tasks.

What they must not control:
- Tenant business analytics, insights, recommendations, or simulations.
- User/role modifications within tenant accounts.
- Billing, subscription, or plan changes of any kind.
- Global platform settings or infrastructure configuration.
- Destructive tenant actions (suspension, deletion, data purge).
- Any AlpMark Super Admin level controls.
- Access to tenant environments outside of active assigned support scope.

PER-08 refinements (agreed):
- All tenant environment access is read-only by default; elevated write access requires Super Admin grant per incident.
- Support access is time-limited per ticket and automatically revoked on ticket closure.
- Support Operator cannot view sensitive tenant financial assumption data unless explicitly escalated and logged.


## Step 4 - User Journeys (In progress)

### JRN-01: Tenant Provisioning (Approved)
Persona: PER-07 AlpMark Super Admin

Goal: Provision a new D2C brand's tenant account so the Brand Admin can begin onboarding their team and connecting their data sources.

Trigger: A new customer has signed up or been onboarded commercially. Super Admin needs to create their account in the platform.

Preconditions:
- Commercial agreement or signup is confirmed.
- Brand name, primary contact email, and plan tier are known.
- Super Admin is authenticated into the AlpMark platform.

Main Flow:
1. Super Admin navigates to tenant management in AlpMark.
2. Creates a new tenant account with brand name, plan tier, and seat limit.
3. Sets the primary contact as the Brand Admin for that tenant.
4. System sends an invite email to the Brand Admin with a secure account activation link.
5. Super Admin confirms tenant is created and status is active.
6. Super Admin verifies plan entitlements are correctly applied (features, seat count, data source limits).
7. Tenant appears in the global tenant directory with status: Active, Pending Setup.

Alternate Flows:
- Brand Admin email is incorrect or bounces: Super Admin can update email and resend invite.
- Wrong plan tier selected: Super Admin can modify plan before Brand Admin activates.
- Duplicate tenant detected (same brand name or email): System warns, Super Admin resolves before proceeding.
- Super Admin needs to suspend a tenant: can set status to Suspended, which blocks all user logins for that tenant.

Outcome:
Tenant account exists, is active, and Brand Admin has received an invite to begin setup. No business data is connected yet.

AlpMark vs External:
- AlpMark: tenant creation, invite generation, plan assignment, status tracking.
- External: commercial agreement, brand communication outside the platform.


### JRN-02: Brand Admin Onboarding (Approved)
Persona: PER-06 Brand Admin

Goal: Complete initial setup of the AlpMark account so the brand's team can log in and start using the platform with connected data sources.

Trigger: Brand Admin clicks the activation link in their invitation email from AlpMark.

Preconditions:
- Tenant account has been created by Super Admin.
- Brand Admin has received the activation email and clicked the secure activation link.
- The link is still valid (not expired).

Main Flow:
1. Brand Admin lands on account creation page with email pre-filled.
2. Brand Admin creates a password and completes first-time account setup.
3. Brand Admin is logged into the AlpMark account.
4. Brand Admin is prompted to start onboarding checklist.
5. Brand Admin navigates to Integrations section.
6. For each data source (Shopify, Meta, Google Ads, etc.):
   - Brand Admin clicks Connect for that source.
   - AlpMark uses the source platform's supported authentication method (OAuth where supported, API key/token where required).
   - Brand Admin authenticates with their brand's external account and authorizes AlpMark access.
   - AlpMark creates a tenant-specific integration connection and triggers initial sync.
   - Brand Admin returns to AlpMark and sees connection and sync status.
7. Brand Admin confirms integration health.
8. Brand Admin navigates to Users section.
9. Brand Admin invites team members by email, assigning roles.
10. System sends invite emails to each team member.
11. Brand Admin marks onboarding as complete.
12. System confirms account is ready for use.

Alternate Flows:
- Authentication fails or user denies permission: Brand Admin can retry or skip and reconnect later.
- Invite email bounces: Brand Admin can update email and resend.
- User invitation expires: Brand Admin can resend.
- Sync fails after integration connect: Brand Admin receives alert but can continue onboarding and troubleshoot later.
- Brand Admin leaves mid-onboarding: can resume from checkpoint on next login.

Outcome:
Brand Admin account is fully set up, at least one data source is connected and syncing, and team members have been invited with appropriate roles assigned. The brand is ready to begin using AlpMark.

AlpMark vs External:
- AlpMark: account creation, password setup, integration connection management, user invitations, sync orchestration, onboarding tracking.
- External: authentication/authorization with the brand's own external systems, email verification by invitees.

Risk/Pain Points:
- Source platform auth flow changes or rejects connection.
- Brand Admin lacks required permissions in external systems.
- Sync fails silently or takes longer than expected, causing confusion.
- Team members do not receive invite emails.
- Role assignment mistakes cause access issues.
- Multiple integrations fail, leaving data gaps.
- Brand Admin abandons onboarding mid-way.
- OAuth token expires after initial connection, causing sync failure; Brand Admin must re-authorize.
- Delayed re-authorization after token expiry compromises data freshness across the account.

Note: Discounts and custom pricing handled outside AlpMark in Phase 1.

---

### JRN-03 Executive Owner Strategic Review — PER-01 (Approved)

Goal:
Executive Owner opens AlpMark to assess overall business health, review prioritized alerts and recommendations, run or review a strategic simulation, and log their approval or dismissal decision — all within AlpMark. No changes are made to external systems from within AlpMark.

Trigger:
Executive Owner logs in for a scheduled weekly review, or receives an alert notification indicating a significant KPI drift or high-impact recommendation requiring attention.

Preconditions:
- At least one data source is connected and has synced within the last 7 days.
- Step-2 KPIs and targets have been configured.
- At least one recommendation or alert exists in the system.

Main Flow:
1. Executive Owner logs into AlpMark and lands on the Executive Dashboard.
2. Dashboard displays: current-period revenue, profit, contribution margin, trend direction, and KPI drift indicators against targets.
3. Executive Owner reviews the Priority Alert panel — alerts ranked by expected business impact.
4. Executive Owner opens a specific recommendation (e.g., "Reallocate budget from Channel A to Channel B — projected +12% contribution margin").
5. AlpMark shows: recommendation rationale, supporting data, confidence level, data freshness indicator, and projected impact simulation.
6. Executive Owner reviews an existing simulation or launches a new strategic simulation (e.g., what-if on pricing or channel mix).
7. AlpMark runs simulation and returns projected outcomes — no external system is changed.
8. Executive Owner approves or dismisses the recommendation inside AlpMark. Decision is logged with timestamp and identity.
9. Recommendation status updates to Approved or Rejected in AlpMark's decision log.
10. Executive Owner reviews cross-team roll-up: growth, retention, finance, operations summaries.
11. Executive Owner sets or updates a business target or alert threshold if needed.
12. Session ends. All decisions and reviews are logged for audit.

Alternate Flows:
- Data freshness warning: if last sync > 7 days, AlpMark surfaces a stale-data warning before showing recommendations. Executive Owner can proceed with caveat or go to Integrations to trigger re-sync.
- Confidence level is low on a recommendation: AlpMark flags it; Executive Owner can defer or dismiss rather than approve.
- No alerts/recommendations exist: Executive Owner sees baseline dashboard with KPI trends only — no false urgency generated.
- Executive Owner wants to delegate approval: can assign recommendation to another eligible user per the delegation rule (PER-01 operational refinement).

Outcome:
Executive Owner has reviewed business health, logged a decision (approve or dismiss) on at least one recommendation, and optionally updated targets or alert preferences. Decision is traceable and stored. No external system has been changed by AlpMark.

AlpMark vs External:
- AlpMark: executive dashboard, KPI drift calculation, alert prioritization, recommendation display, simulation engine, decision logging, audit trail.
- External: any actual change resulting from an approved recommendation is carried out manually by the responsible team member in the relevant external platform.

Risk/Pain Points:
- Stale data leads to low-confidence recommendations; Executive Owner cannot trust what they see.
- Too many alerts with no prioritization causes signal fatigue — high-impact items get missed.
- Recommendation approved in AlpMark but never implemented externally — outcome tracking shows no change; system flags implementation gap.
- Delegation rule not configured; Executive Owner is the only approver and becomes a bottleneck.
- KPI targets not set; drift indicators cannot fire; dashboard shows raw numbers with no context.

---

### JRN-04 Growth and Performance Manager Channel Performance Review — PER-02 (Approved)

Goal:
Growth and Performance Manager opens AlpMark to review channel and campaign efficiency, identify underperforming or overspending areas, run a spend reallocation simulation, and log an approval or dismissal decision on a budget recommendation — all within AlpMark. No changes are pushed to any ad platform from AlpMark.

Trigger:
Growth and Performance Manager logs in for a routine performance review, or receives an early-warning alert that a channel's ROAS or CAC has crossed a configured threshold.

Preconditions:
- At least one ad platform (e.g., Meta, Google Ads) is connected, syncing, and data is fresh.
- Channel/campaign cost and revenue data is available in AlpMark.
- At least one active recommendation or alert exists related to channel spend or efficiency.

Main Flow:
1. Growth and Performance Manager logs into AlpMark and lands on the Channel Performance dashboard.
2. Dashboard displays: spend by channel, ROAS, CAC, payback period, trend direction, and blended profitability impact — current period vs prior period.
3. Manager reviews the Early Warning panel — alerts flagging declining performance or inefficient spend pockets, ranked by projected margin impact.
4. Manager opens a specific budget reallocation recommendation (e.g., "Shift 20% of Meta budget to Google Search — projected CAC reduction of 15%").
5. AlpMark displays: recommendation rationale, supporting channel data, confidence level, data freshness indicator, and projected KPI impact.
6. Manager runs a spend simulation: adjusts channel budget split and AlpMark projects the impact on CAC, ROAS, and contribution margin — no change is made to any external platform.
7. Manager compares simulation scenarios side by side.
8. Manager approves or rejects the recommendation inside AlpMark. Decision is logged with timestamp and identity.
9. Recommendation status updates to Approved or Rejected in AlpMark's decision log.
10. Manager adds an annotation or saves the analysis view for later reference or executive sharing.
11. Manager exports or shares a decision summary for executive review if needed.

Alternate Flows:
- Data freshness warning: if ad platform sync is stale, AlpMark flags it before showing recommendations. Manager can proceed with caveat or go to Integrations.
- Multiple conflicting recommendations exist: Manager can compare them and flag one for further review without approving yet.
- Simulation produces unexpected results: Manager can reset assumptions and re-run without affecting any external system.
- No active recommendations: Manager sees performance trends and early warnings only — dashboard does not fabricate urgency.
- Alert threshold not configured: Early Warning panel is empty; Manager can set thresholds from the alerts configuration.

Outcome:
Growth and Performance Manager has reviewed channel performance, logged a spend decision (approve or reject) on at least one recommendation, and optionally saved an analysis view or exported a summary. No ad platform has been changed by AlpMark. The decision is traceable and stored.

AlpMark vs External:
- AlpMark: channel performance dashboard, early warning alerts, recommendation display, simulation engine, decision logging, annotation/view saving, export of decision summaries.
- External: any actual budget change resulting from an approved recommendation is carried out manually by the manager in the relevant ad platform (Meta Ads Manager, Google Ads, etc.).

Risk/Pain Points:
- Ad platform sync is delayed or stale; recommendations are based on outdated spend data.
- ROAS/CAC calculations depend on accurate cost data from ad platforms and revenue data from Shopify — a gap in either makes recommendations unreliable.
- Recommendation approved in AlpMark but the external change is not made or is made incorrectly — outcome tracking shows no improvement; system should flag implementation gap.
- Manager over-relying on simulations without accounting for external factors (creative fatigue, seasonality) not captured in AlpMark data.
- Alert thresholds not configured; early warnings never fire; declining performance goes unnoticed until significant damage.


---

### JRN-05 Retention and CRM Manager Cohort Health Review — PER-03 (Approved)

Goal:
Retention and CRM Manager opens AlpMark to review cohort retention curves, identify at-risk customer segments, evaluate a retention recommendation, and log an approval or dismissal decision — all within AlpMark. No messages, campaigns, or automations are executed from AlpMark.

Trigger:
Retention Manager logs in for a routine cohort review, or receives an alert that a cohort's repeat purchase rate or a segment's churn risk indicator has crossed a configured threshold.

Preconditions:
- Shopify order data is connected, syncing, and fresh enough to generate cohort curves.
- Customer lifecycle and segment data is available in AlpMark.
- At least one retention recommendation or churn-risk alert exists.

Main Flow:
1. Retention Manager logs into AlpMark and lands on the Retention and Cohort dashboard.
2. Dashboard displays: repeat purchase rate trend, cohort retention curves (per time-period cohort), customer lifecycle funnel (first order → second order → repeat cadence), and segment contribution margin.
3. Manager reviews churn-risk and drop-off indicators by segment and time window (0-30, 30-60, 60-90 days post first purchase).
4. Manager uses side-by-side cohort comparison to identify which cohort is underperforming and why.
5. Manager checks read-only acquisition metrics (channel, CAC, new customer quality) to understand the quality of customers retention is working with.
6. Manager reviews return/refund behavior as a retention signal (e.g., high return rate in a cohort correlates with lower repeat rate).
7. Manager opens a specific retention recommendation (e.g., "Increase win-back touchpoint frequency for 30-60 day at-risk cohort — projected +8% repeat rate").
8. AlpMark displays: recommendation rationale, supporting cohort data, confidence level, data freshness indicator, and projected margin impact.
9. Manager runs a retention simulation: adjusts assumptions (response rate, timing, segment scope, intensity) and AlpMark projects the outcome — no external CRM or automation tool is changed.
10. Manager compares simulation scenarios.
11. Manager approves or rejects the recommendation inside AlpMark. Decision is logged with timestamp and identity.
12. Recommendation status updates to Approved or Rejected in AlpMark's decision log.
13. Manager annotates a lifecycle event if relevant (e.g., sale period, catalog change) for context.
14. Manager exports or shares a retention decision summary with Executive Owner, Growth, or Finance stakeholders if needed.

Alternate Flows:
- Data freshness warning: if Shopify sync is stale, AlpMark surfaces warning before showing cohort data. Manager can proceed with caveat or go to Integrations.
- Confidence level is low due to small cohort size: AlpMark flags statistical limitation; Manager can note it and defer or proceed with awareness.
- No retention recommendations exist: Manager sees cohort trends and churn indicators only — no false urgency.
- Alert threshold not configured: churn-risk alerts do not fire; Manager can configure thresholds from the alerts section.
- Manager wants to save a custom segment view for repeated use: can build and save from the segment panel.

Outcome:
Retention Manager has reviewed cohort health, identified at-risk segments, logged a decision (approve or reject) on at least one retention recommendation, and optionally annotated a lifecycle event or shared a summary. No CRM or automation tool has been changed by AlpMark. The decision is traceable and stored.

AlpMark vs External:
- AlpMark: cohort dashboard, churn-risk indicators, lifecycle funnel, retention recommendation display, simulation engine, decision logging, annotation, export of decision summaries.
- External: any actual retention action (campaign send, flow trigger, discount offer) resulting from an approved recommendation is carried out manually by the manager in the relevant CRM or marketing automation tool.

Risk/Pain Points:
- Shopify sync delay means cohort curves are stale; at-risk identification is lagging.
- Small cohort sizes reduce statistical confidence; AlpMark must flag this clearly to avoid over-confident recommendations.
- Recommendation approved in AlpMark but external campaign not executed — outcome tracking shows no repeat rate improvement; system should flag implementation gap.
- Return/refund data used as a retention signal requires clean order and return tagging from Shopify — data quality issues upstream corrupt the signal.
- Lifecycle annotations not maintained; context for cohort anomalies is lost, making trend interpretation unreliable.


---

### JRN-06 Finance Controller Margin Review and Cost Input Governance — PER-04 (Approved)

Goal:
Finance Controller opens AlpMark to review the contribution margin breakdown, investigate a cost variance or drift alert, and update a cost input — either validating a synced value or providing a manual input where no connected source exists. All changes are versioned and impact-previewed before taking effect. No changes are made to external finance or ERP systems from AlpMark.

Cost Input Sourcing Rule (applies throughout this journey):
- AlpMark always prefers real data from connected sources (Shopify COGS, actual return data, connected shipping platform). These are synced automatically and do not require manual input.
- Manual inputs are only required where no connected source exists (e.g., 3PL costs not in any API, return processing/restocking costs, COGS not maintained in Shopify).
- Every metric is labelled by source (synced vs manual) and carries a corresponding confidence indicator. Manual inputs show lower confidence than synced data.

Trigger:
Finance Controller logs in for a routine weekly/monthly margin review, or receives a drift alert that actual margin has deviated beyond a configured threshold for a channel, product, or order type.

Preconditions:
- Revenue and cost data (Shopify orders, ad spend, Shopify COGS where available) is connected and syncing.
- At least one cost input has been previously configured (synced or manual).
- Margin drift thresholds have been set.

Main Flow:
1. Finance Controller logs into AlpMark and lands on the Finance and Margin dashboard.
2. Dashboard displays: contribution margin breakdown by channel, product, and order type — current period vs prior period, actual vs expected. Each cost input is labelled: synced (with source and last sync time) or manual (with last updated date and owner).
3. Finance Controller reviews the Drift Alert panel — flags where actual margin has deviated beyond threshold, with variance reason context.
4. Finance Controller drills into a specific variance (e.g., shipping cost increase driving margin compression on a product category).
5. AlpMark shows: cost driver breakdown (COGS, shipping, returns, discounts, ad spend), data freshness indicator, confidence level, and source label for each input.
6. Finance Controller identifies the cost input that needs updating.
   - If the input is synced: Finance Controller validates it, and if the source data is wrong, resolves it in the connected source system (outside AlpMark).
   - If the input is manual: Finance Controller updates the value in AlpMark, sets an effective date (immediate or scheduled), and adds a variance reason tag (e.g., "carrier rate increase May 2026").
7. If the change is high-impact, AlpMark requires an explicit approval lock before the updated input is applied to live recommendations and simulations.
8. Finance Controller reviews the financial impact preview — AlpMark shows how the updated input changes contribution margin, affected recommendations, and simulation outcomes.
9. Finance Controller confirms and saves the change. AlpMark versions the change with timestamp and identity.
10. Finance Controller runs a finance-lens simulation if needed (e.g., what-if on return rate reduction — projected margin uplift).
11. Finance Controller reviews the historical cost input change log to verify audit trail.
12. Finance Controller exports a finance summary or reporting view for leadership or governance use if needed.

Alternate Flows:
- Data freshness warning: if cost/revenue sync is stale, AlpMark flags it before showing margin outputs. Finance Controller can proceed with caveat or go to Integrations.
- Synced cost input is incorrect: Finance Controller cannot override it in AlpMark — must fix it in the source system. AlpMark shows a note explaining this.
- Cost input change has downstream impact on pending recommendations: AlpMark highlights affected recommendations and flags them for re-review before the change is applied.
- Finance Controller wants to restate a historical period under prior vs new inputs: can run a restatement comparison from the cost input history panel.
- Finance Controller wants to defer a high-impact change: can save as draft with scheduled effective date rather than applying immediately.
- Drift alert threshold not configured: no alerts fire; Finance Controller can configure thresholds by channel/category from the alerts settings.

Outcome:
Finance Controller has reviewed margin performance, identified and resolved a cost variance, updated a cost input with full version history and audit trail, and validated the downstream financial impact. No external finance or ERP system has been changed by AlpMark. The change is traceable and stored.

AlpMark vs External:
- AlpMark: margin dashboard, drift alerts, cost driver breakdown, cost input management (synced validation + manual entry), version control, approval lock, simulation engine, restatement comparison, finance export.
- External: any actual cost negotiation, pricing change, or financial system update resulting from insights is carried out manually outside AlpMark. If a synced cost input is wrong, the correction is made in the source system, not in AlpMark.

Risk/Pain Points:
- COGS not maintained in Shopify — a large portion of cost inputs fall back to manual entry, reducing confidence across all margin outputs.
- 3PL or carrier costs not available via API — Finance Controller must manually update these; if not kept current, margin outputs drift silently.
- High-impact cost input change applied without approval lock — downstream recommendations become unreliable without other personas knowing why.
- Synced input is wrong but Finance Controller tries to override it in AlpMark — system must clearly communicate that the fix must happen at the source.
- Drift thresholds too broad or not configured per channel/category; real variances are masked by global averages.
- Historical restatement not run after major cost input changes — audit trail exists but business decisions were made on outdated margin figures.


---

### JRN-07 Operations and Inventory Manager Inventory Risk Review — PER-05 (Approved)

Goal:
Operations and Inventory Manager opens AlpMark to review inventory health across SKUs and warehouses, identify stockout and overstock risks, evaluate an operational recommendation, run a simulation, and log an approval or dismissal decision — all within AlpMark. No changes are made to any ERP, WMS, or 3PL system from AlpMark.

Trigger:
Operations Manager logs in for a routine inventory health review, or receives an operational anomaly alert — stockout risk, return spike, or shipping-cost spike — that has crossed a configured threshold.

Preconditions:
- Inventory and order data (Shopify, or connected inventory/3PL source) is syncing and fresh.
- At least one SKU or category has a risk signal (low stock, overstock, elevated return rate).
- Operational alert thresholds have been configured.

Main Flow:
1. Operations Manager logs into AlpMark and lands on the Inventory and Operations dashboard.
2. Dashboard displays: inventory health by SKU and category — in-stock, low-stock, stockout risk (with days-to-stockout estimate), overstock risk, and slow-moving inventory signals.
3. Where multiple fulfillment nodes exist, the view shows inventory health per warehouse/location.
4. Manager reviews the Operational Anomaly Alert panel — stockout clusters, return spikes, shipping-cost spikes — ranked by projected margin impact.
5. Manager opens a specific risk alert (e.g., "SKU-042 at primary warehouse — estimated stockout in 6 days, projected lost revenue £18,000 and repeat purchase risk for 240 customers").
6. AlpMark displays: stockout impact estimate on lost revenue and repeat purchase risk, fulfillment and logistics cost impact on contribution margin, return/refund operational patterns for the affected SKU.
7. Manager opens a specific operational recommendation (e.g., "Expedite reorder for SKU-042 — projected margin impact +£14,000 vs stockout scenario").
8. AlpMark displays: recommendation rationale, supporting inventory data, confidence level, data freshness indicator, and projected margin impact with upside/downside view.
9. Manager runs an operational simulation: adjusts assumptions (reorder timing, reorder quantity, return-cost assumptions, shipping-cost change) and AlpMark projects the outcome — no ERP or WMS is changed.
10. Manager compares simulation scenarios.
11. Manager approves or rejects the recommendation inside AlpMark. Decision is logged with timestamp and identity.
12. Recommendation status updates to Approved or Rejected in AlpMark's decision log.
13. Manager adds an operational context annotation if relevant (e.g., "supplier delay confirmed — lead time extended 14 days").
14. Manager exports an ops impact summary for leadership decision review if needed.
15. After the external action has been taken (outside AlpMark), Manager tracks the recommendation lifecycle — AlpMark infers outcome from synced inventory and order data and surfaces the observed result with an external-action evidence marker (what changed, source, sync timestamp).

Alternate Flows:
- Data freshness warning: if inventory sync is stale, AlpMark surfaces warning before showing risk signals. Manager can proceed with caveat or go to Integrations.
- Multi-warehouse view: if stock is healthy at one warehouse but not another, AlpMark surfaces the location-level breakdown — Manager can evaluate redistribution vs reorder.
- Confidence level is low due to limited SKU history: AlpMark flags it; Manager can note and proceed with awareness.
- No anomaly alerts exist: Manager sees inventory health trends only — no false urgency.
- Alert thresholds not configured: anomaly alerts do not fire; Manager can configure from the alerts settings.

Outcome:
Operations Manager has reviewed inventory health, identified and logged a decision on at least one operational risk recommendation, and optionally annotated context or exported a summary. No ERP, WMS, or 3PL system has been changed by AlpMark. The decision is traceable and stored. Outcome is tracked via synced data after external implementation.

AlpMark vs External:
- AlpMark: inventory health dashboard, anomaly alerts, stockout impact estimates, recommendation display, simulation engine, decision logging, annotation, outcome tracking via synced data.
- External: any actual reorder, stock transfer, return policy change, or fulfillment adjustment resulting from an approved recommendation is carried out manually by the manager in the relevant ERP, WMS, or 3PL system.

Risk/Pain Points:
- Inventory sync is delayed or partial — stockout risk estimates are lagging and the alert fires too late.
- Days-to-stockout estimate depends on accurate sales velocity data; a demand spike not yet synced produces a false-safe signal.
- Recommendation approved in AlpMark but reorder not placed externally — outcome tracking shows continued stockout; system should flag implementation gap.
- Multi-warehouse view relies on inventory data per location being available from the connected source — many brands do not have this cleanly in Shopify.
- Operational annotations not maintained — context for anomalies (supplier delays, warehouse issues) is lost, making historical trend interpretation unreliable.
- Return operational view and retention return signal must remain completely separate dashboards with distinct metrics — if mixed, confusion results: Operations Manager may dismiss a 22% return rate as a cost-managed SKU characteristic, while Retention Manager sees the same rate and flags a cohort as at-risk churn. Each view answers different questions (operational cost burden vs customer satisfaction/repeat behaviour) and uses different data slices (by SKU and cost vs by cohort and repeat-purchase correlation). Sharing the same "Returns" view risks both personas making decisions on incomplete signals.


---

### JRN-08 AlpMark Support/Admin Operator Tenant Support and Diagnostics — PER-08 (Approved)

Goal:
AlpMark Support Operator receives a support ticket from a Brand Admin, accesses the tenant environment in read-only mode to diagnose the issue, resolves or escalates it, and logs all actions — all within AlpMark's support tooling. The operator never modifies tenant business data, analytics, or user/role configurations.

Trigger:
A Brand Admin raises a support ticket — typically for an integration failure, sync error, onboarding confusion, or platform configuration issue.

Preconditions:
- A support ticket has been assigned to the Support Operator.
- Support Operator is authenticated into AlpMark with their support-scoped access.
- The ticket is within the operator's active assigned support scope (access outside active scope is not permitted).

Main Flow:
1. Support Operator opens their support queue and selects the assigned ticket.
2. Ticket shows: Brand Admin's reported issue, tenant ID, current integration health, sync status, and any related error logs.
3. Support Operator enters the tenant environment in read-only mode to investigate.
4. Operator reviews tenant account status: plan, seat count, user list (read-only), integration connection health, sync error details, and onboarding completion state.
5. Operator reviews integration and connector diagnostic information to identify the root cause (e.g., OAuth token expired, API rate limit hit, sync job failed silently).
6. Operator guides the Brand Admin through the resolution — for example, instructing them to re-authenticate their Shopify OAuth token or reconnect a failed integration.
7. If the issue requires a manual data re-sync, Operator triggers it from within the support tooling.
8. If elevated write access is needed to resolve the issue (beyond read-only), Operator requests a time-limited elevated access grant from AlpMark Super Admin. Grant is logged.
9. Operator adds internal support notes and a resolution log to the ticket throughout.
10. If the issue cannot be resolved at support level, Operator escalates to AlpMark Super Admin with full diagnostic context.
11. On resolution, ticket is closed. Support access to the tenant environment is automatically revoked.
12. All support actions within the tenant environment are logged in the audit trail.

Alternate Flows:
- Issue is an integration auth failure (OAuth token expired): Operator cannot re-authenticate on behalf of the Brand Admin — guides Brand Admin to do it themselves. Operator documents the steps taken.
- Tenant environment access required but ticket is not actively assigned: access is denied by the system; Operator must have an active ticket assignment to enter the tenant environment.
- Elevated write access needed but Super Admin is unavailable: Operator escalates and waits; cannot self-grant elevated access.
- Brand Admin is mid-onboarding and needs guidance: Operator walks them through the onboarding checklist, does not modify configuration directly.
- Issue is a platform-level bug affecting multiple tenants: Operator escalates immediately to Super Admin and flags cross-tenant impact.

Outcome:
Support ticket is resolved or escalated with full resolution log. Brand Admin's issue is addressed. All operator actions within the tenant environment are audited. Tenant environment access is revoked on ticket closure. No tenant business data, user roles, billing, or analytics have been modified by the operator.

AlpMark vs External:
- AlpMark: support ticket management, read-only tenant environment access, integration diagnostics, manual re-sync trigger (limited), internal notes and resolution logging, audit trail of support actions, escalation to Super Admin.
- External: any credential re-authentication (OAuth re-authorization, API key rotation) is performed by the Brand Admin in the relevant external platform — the Support Operator guides but does not execute.

Risk/Pain Points:
- Support Operator accesses tenant environments outside of active ticket scope — system must enforce assignment-scoped access strictly.
- Support access not automatically revoked on ticket closure — time-limited access grant must be enforced by the system, not reliant on manual revocation.
- Operator attempts to re-authenticate OAuth on behalf of Brand Admin — this must be blocked; only the Brand Admin can authorize AlpMark's access to their external accounts.
- Sensitive tenant financial data (cost inputs, margin assumptions) accessed during support — must be explicitly blocked unless escalated, logged, and approved.
- Support notes and resolution logs not maintained — future support incidents for the same tenant have no history context.
- Operator self-grants elevated write access without Super Admin approval — must be architecturally prevented, not just policy-restricted.


---

## Step 5 - Epics (Approved)

### EPC-01 Tenant and Account Management (Approved)

What it covers:
Everything needed to create and manage a brand's account on AlpMark — from Super Admin provisioning a new tenant, to Brand Admin setting up users and roles, to billing and subscription management.

Personas: PER-07, PER-06, PER-01
Journeys: JRN-01, JRN-02

Key capabilities:
- Tenant creation, plan assignment, seat limits (Super Admin).
- Brand Admin account activation and onboarding checklist.
- User invitation, role assignment, access approval, deactivation.
- Billing operations: payment method, seat management, invoices, plan changes.
- Platform notification routing configuration.
- Audit log of all access, role, and billing events within the tenant.

---

### EPC-02 Data Integration and Sync (Approved)

What it covers:
All connectivity between AlpMark and external data sources — connecting platforms, managing auth credentials, running sync jobs, handling failures, and surfacing data freshness status.

Personas: PER-06, PER-07, PER-08
Journeys: JRN-02

Key capabilities:
- OAuth and API key connection flows per supported source (Shopify, Meta, Google Ads, etc.).
- Tenant-isolated credential storage and management.
- Automated scheduled sync jobs per connected source.
- Token expiry detection and Brand Admin re-authorization alerts.
- Manual re-sync trigger (Brand Admin and Support Operator).
- Sync status, last synced timestamp, and error reporting per source.
- Data freshness indicators surfaced across the platform.

---

### EPC-03 Executive Intelligence and KPI Tracking (Approved)

What it covers:
The executive-level view of business health — unified KPI dashboard, drift detection against targets, prioritised alerts, and cross-team roll-up.

Personas: PER-01
Journeys: JRN-03

Key capabilities:
- Executive dashboard: revenue, profit, contribution margin, trend direction.
- KPI drift indicators vs configured targets.
- Priority alert panel ranked by expected business impact.
- Cross-team performance roll-up (growth, retention, finance, operations) with drill-down.
- Business target and alert preference configuration.
- Delegation rule for executive recommendation approvals.
- Stale data warning before recommendations are displayed.

---

### EPC-04 Channel and Acquisition Performance (Approved)

What it covers:
Channel and campaign efficiency views for the Growth and Performance Manager — spend analysis, ROAS, CAC, early warnings, and blended profitability impact.

Personas: PER-02, PER-01 (read-only roll-up)
Journeys: JRN-04

Key capabilities:
- Channel performance dashboard: spend, ROAS, CAC, payback, trend by channel.
- Blended and channel-level profitability impact view.
- Early warning panel: declining performance and inefficient spend alerts.
- Campaign-level drill-down.
- Performance alert threshold configuration per channel.
- Analysis view saving and annotation.
- Decision summary export for executive sharing.

---

### EPC-05 Retention and Cohort Analytics (Approved)

What it covers:
Customer retention intelligence — cohort retention curves, lifecycle funnel, churn-risk indicators, segment performance, and return behaviour as a retention signal.

Personas: PER-03, PER-02 (acquisition read-only), PER-01 (roll-up)
Journeys: JRN-05

Key capabilities:
- Repeat purchase rate trends and cohort retention curves (per time-period cohort).
- Side-by-side cohort comparison.
- Customer lifecycle funnel: first order → second order → repeat cadence.
- Churn-risk and drop-off indicators by segment and time window (0-30, 30-60, 60-90 days).
- Segment-level contribution margin view.
- Return/refund behaviour as a retention signal (separate from operational returns view).
- Read-only acquisition metrics (channel, CAC, new customer quality) for retention context.
- Custom segment view creation and saving.
- Lifecycle event annotation.
- Retention decision summary export.

---

### EPC-06 Financial Governance and Margin Intelligence (Approved)

What it covers:
Contribution margin visibility, cost input management (synced and manual), drift detection, assumption versioning, approval lock, and historical restatement.

Personas: PER-04, PER-01 (roll-up)
Journeys: JRN-06

Key capabilities:
- Contribution margin breakdown by channel, product, and order type.
- Cost driver visibility: COGS, shipping, returns, discounts, ad spend impact.
- Two-tier cost input model: synced (from connected sources) vs manual (where no source exists).
- Source label and confidence indicator on every cost input and derived metric.
- Cost input update with effective date, variance reason tag, and version history.
- Approval lock for high-impact cost input changes before live propagation.
- Drift alerts per channel/category with configurable thresholds.
- Finance-lens simulation using cost input assumptions.
- Historical restatement: prior vs new cost input comparison.
- Finance summary export for leadership/governance.

---

### EPC-07 Inventory and Operations Intelligence (Approved)

What it covers:
Inventory health monitoring, stockout and overstock risk detection, fulfillment cost impact, return operational patterns, and anomaly alerts — across SKUs, categories, and warehouse locations.

Personas: PER-05, PER-01 (roll-up)
Journeys: JRN-07

Key capabilities:
- Inventory health dashboard by SKU and category: in-stock, low-stock, stockout risk (with days-to-stockout), overstock, slow-moving.
- Multi-warehouse/location inventory view where data is available.
- Stockout impact estimates: lost revenue and repeat purchase risk.
- Fulfillment and logistics cost impact on contribution margin.
- Return/refund operational view by SKU and cost — completely separate from retention return signal.
- Operational anomaly alert panel: stockout clusters, return spikes, shipping-cost spikes.
- Operational context annotation (supplier delay, warehouse issue, policy change).
- Outcome tracking via synced data after external implementation, with evidence marker.
- Ops impact summary export.

---

### EPC-08 Recommendation and Decision Engine (Approved)

What it covers:
The cross-cutting engine that generates, surfaces, and tracks recommendations across all domains — and records every approval, rejection, and outcome in a traceable decision log.

Personas: PER-01, PER-02, PER-03, PER-04, PER-05
Journeys: JRN-03, JRN-04, JRN-05, JRN-06, JRN-07

Key capabilities:
- Recommendation generation per domain (growth, retention, finance, ops) with rationale, supporting data, confidence level, and projected impact.
- Recommendation status lifecycle: New → Reviewed → Approved → Rejected → Implemented externally → Outcome observed.
- Approval and rejection logging with timestamp and identity.
- Delegation rule: recommendation assignment to eligible users.
- Implementation gap detection: approved recommendation with no observed outcome change flagged.
- Outcome tracking: inferred from synced data post external implementation with evidence marker.
- Recommendation filtering and prioritisation by impact.
- Decision summary export.

---

### EPC-09 Simulation Engine (Approved)

What it covers:
The what-if modelling capability used across all analytical personas — adjusting inputs and projecting outcomes without changing anything in any external system.

Personas: PER-01, PER-02, PER-03, PER-04, PER-05
Journeys: JRN-03, JRN-04, JRN-05, JRN-06, JRN-07

Key capabilities:
- Simulation framework: adjust input assumptions → project outcome metrics.
- Domain-specific simulation inputs: budget split (growth), response rate/timing/segment (retention), cost inputs (finance), reorder timing/quantity (ops), pricing/channel mix (executive).
- Upside and downside projection view.
- Side-by-side scenario comparison.
- Confidence and data freshness indicator on simulation outputs.
- Simulation results do not affect live recommendations or external systems.
- Save and revisit simulation scenarios.

---

### EPC-10 Support and Diagnostics Tooling (Approved)

What it covers:
Internal tooling for AlpMark Support Operators to handle tenant support tickets, diagnose integration and sync issues, and escalate to Super Admin — with full audit logging and access controls.

Personas: PER-08, PER-07
Journeys: JRN-08

Key capabilities:
- Support ticket queue and assignment management.
- Read-only tenant environment access scoped to active assigned tickets.
- Tenant diagnostic view: account status, integration health, sync errors, user list (read-only).
- Manual re-sync trigger (support-scoped).
- Time-limited elevated access request workflow (requires Super Admin grant, logged).
- Internal support notes and resolution log per ticket.
- Automatic access revocation on ticket closure.
- Escalation to Super Admin with full diagnostic context.
- Audit log of all support operator actions within tenant environments.
- Block on operator accessing sensitive financial data without explicit escalation approval.

---

### EPC-11 Notifications and Alert Infrastructure (Approved)

What it covers:
The cross-cutting alert and notification layer that powers early warnings, KPI drift alerts, data freshness warnings, and confidence flags across all personas and domains. Supports two distinct alert trigger types: threshold-based (persona-configured) and anomaly-based (system-detected).

Personas: All (PER-01 through PER-08)
Journeys: All

Alert Trigger Types (agreed):
- Threshold alerts: persona-configured, domain-specific. A limit set by the persona is breached (e.g., CAC > £45, repeat purchase rate < 30%, contribution margin < 25% on Category X). Predictable and user-controlled. AlpMark fires when the threshold is crossed.
- Anomaly alerts: system-detected, no pre-configuration required. AlpMark identifies a statistically significant deviation from recent trend or baseline (e.g., return rate on a SKU spikes 3x in 48 hours, ad spend drops to zero unexpectedly, revenue drops 40% day-on-day with no seasonal pattern). Catches issues the persona did not think to watch for.

Key capabilities:
- Threshold alert configuration per persona and per domain (not one global setting).
- Channel/category-level threshold profiles.
- Anomaly detection per domain: statistical deviation from recent trend or baseline, auto-generated without persona pre-configuration.
- Alert types covered: KPI drift, stockout risk, churn risk, sync failure, token expiry, margin drift, early performance warning, operational anomaly.
- Stale data warning surfaced before recommendations and dashboards are shown.
- Confidence level indicators on all recommendations, simulations, and metrics.
- Notification routing: Brand Admin configures which persona receives which alert type.
- Delivery: in-app and email.
- Alert history and dismissal log.


---

## Step 6 - Functional Requirements (Approved)

### EPC-01 Tenant and Account Management

FR-001 → EPC-01 → PER-07: Super Admin can create a new tenant with brand name, plan tier, seat limit, and primary contact email; system assigns unique tenant ID and enforces data isolation.
FR-002 → EPC-01 → PER-06: Brand Admin activates account via secure activation link, creates password, and is presented with onboarding checklist.
FR-003 → EPC-01 → PER-06: System displays onboarding checklist with checkpoints (integrations connected, users invited, roles assigned); auto-updates as milestones complete.
FR-004 → EPC-01 → PER-06: Brand Admin can invite team members by email, assign roles at invite time; invitee receives activation email.
FR-005 → EPC-01 → PER-06: Brand Admin can view all brand users, modify roles (all roles except Executive Owner), deactivate, and remove users; every change logged in audit trail.
FR-006 → EPC-01 → PER-06: Brand Admin can update payment method, manage seat count, download invoices, and request plan changes (plan changes routed to Executive Owner for approval).
FR-007 → EPC-01 → PER-06: Brand Admin can configure notification routing — specifying which persona receives which alert type and via which channel (in-app, email, or both).
FR-008 → EPC-01 → PER-06/PER-07: System logs all access changes, role modifications, and billing events with timestamp and user ID; audit log is queryable and exportable per tenant with optional email delivery to selected authorized recipients.

---

### EPC-02 Data Integration and Sync

FR-009 → EPC-02 → PER-06: Brand Admin can connect a supported external platform (Shopify, Meta, Google Ads) via OAuth — AlpMark redirects to platform, Brand Admin approves, token returned and stored; sync initiated automatically.
FR-010 → EPC-02 → PER-06: Where OAuth is unavailable, Brand Admin can enter API key/token manually; credential validated on entry, sync initiated.
FR-011 → EPC-02 → System: All OAuth tokens and API keys stored encrypted in a tenant-isolated vault; credentials never logged in plaintext.
FR-012 → EPC-02 → System: System monitors OAuth token expiry; Brand Admin alerted at 7 days before expiry and immediately after expiry, with link to re-authorize.
FR-013 → EPC-02 → PER-06: Brand Admin can re-authorize an expired OAuth token via "Re-authorize" button; new token fetched, old retired, sync resumes automatically.
FR-014 → EPC-02 → System: Automated scheduled sync jobs run per connected source; last synced timestamp updated on every successful sync.
FR-015 → EPC-02 → PER-06/PER-08: Brand Admin or Support Operator can trigger a manual re-sync on demand for any connected source.
FR-016 → EPC-02 → PER-06: Integration panel shows per-source: connected/disconnected status, last synced timestamp, sync progress, and actionable error message on failure.
FR-017 → EPC-02 → System: Every dashboard, metric, and recommendation displays a data freshness indicator (high < 24h, medium < 7d, low > 7d); stale data warning shown before recommendations if data > 7 days old.

---

### EPC-03 Executive Intelligence and KPI Tracking

FR-018 → EPC-03 → PER-01: Executive Owner lands on dashboard showing current revenue, profit, contribution margin, trend direction vs prior period, and KPI summary.
FR-019 → EPC-03 → PER-01: Executive Owner can set or update KPI targets; targets stored with effective date, versioned, and used for drift calculations immediately.
FR-020 → EPC-03 → System: System calculates KPI drift daily: (actual - target) / target; alert fired if drift exceeds configured threshold; confidence shown based on data freshness.
FR-021 → EPC-03 → System: Priority alert panel ranks alerts by projected impact score. Impact score = estimated financial exposure (revenue at risk or margin impact in £) × urgency factor (proximity to point of no return — e.g., stockout in 2 days scores higher than stockout in 14 days). Alert types each have a defined exposure formula: stockout = daily sales velocity × days-to-stockout; margin drift = drift % × revenue in affected area; churn risk = at-risk customer count × average LTV proxy.
FR-022 → EPC-03 → PER-01: Executive Owner views cross-team roll-up: Growth (channel metrics), Retention (cohort health), Finance (margin), Ops (inventory), with drill-down to each domain dashboard.
FR-023 → EPC-03 → PER-01: Executive Owner can set a delegation rule — assigning recommendation approval authority to another qualified user for specified recommendation types; delegation logged in audit trail.
FR-024 → EPC-03 → System: If any data source is stale (> 7 days), stale data warning is prominently displayed before showing recommendations; user can proceed with caveat or go to Integrations.

---

### EPC-04 Channel and Acquisition Performance

FR-025 → EPC-04 → PER-02: Growth Manager lands on dashboard showing spend by channel, ROAS, CAC, payback period, trend vs prior period; campaign-level drill-down available.
FR-026 → EPC-04 → System: ROAS calculated per channel daily: revenue attributed to channel / ad spend on channel; confidence based on data freshness and attribution accuracy.
FR-027 → EPC-04 → System: CAC calculated per channel daily: ad spend on channel / new customers acquired from channel; confidence based on data freshness.
FR-028 → EPC-04 → System: Payback period calculated per channel: time until cumulative revenue exceeds cumulative ad spend based on historical cohort data; upside and downside scenarios shown.
FR-029 → EPC-04 → PER-02: Blended and channel-level contribution margin displayed: (revenue − COGS − shipping − ad spend) / revenue; updated daily.
FR-030 → EPC-04 → System: Early warning alert fires when channel ROAS drops below threshold or CAC rises above threshold; alert ranked by margin impact with clear message.
FR-031 → EPC-04 → PER-02: Growth Manager can configure ROAS and CAC alert thresholds per channel; thresholds effective immediately for next alert check.
FR-032 → EPC-04 → PER-02: Growth Manager can save a custom analysis view (filters, date range) for quick recall and team sharing.
FR-033 → EPC-04 → PER-02: Growth Manager can add annotations to analysis views (e.g., "Creative fatigue — pausing Campaign A"); annotation timestamped and included in exports.
FR-034 → EPC-04 → PER-02: Growth Manager can export and share a decision summary (metrics, recommendations, approvals, annotations) as PDF/CSV and email it to selected recipients. Export can be scoped to selected metrics only (e.g., ROAS-only) and is permission-checked so recipients only receive data they are allowed to view.

---

### EPC-05 Retention and Cohort Analytics

FR-035 → EPC-05 → System: Repeat purchase rate calculated daily: customers with 2+ orders / total customers with at least 1 order; trend vs 30/60/90 days shown; confidence based on cohort size and data freshness.
FR-036 → EPC-05 → System: Cohort retention curves generated per time-period cohort (monthly); % of cohort that repeat-purchased by relative time windows (see FR-039 for cadence definition); updated daily as new repeat purchases sync.
FR-037 → EPC-05 → PER-03: Retention Manager can view two cohorts side-by-side for comparison; overlay curves, highlight differences, export comparison.
FR-038 → EPC-05 → System: Customer lifecycle funnel displayed: first order → second order → repeat cadence; stage-to-stage conversion rates shown; dropoff points highlighted.
FR-039 → EPC-05 → System: Churn risk calculated using brand-specific expected repurchase cadence, not fixed global time windows. System derives the median time between Order 1 and Order 2 from the brand's own historical data — this becomes the baseline expected repurchase window. Time window buckets (early, mid, late at-risk) are expressed as relative multiples of this cadence (e.g., 0–1× expected window = healthy, 1–1.5× = mild risk, 1.5–2× = high risk, 2×+ = likely churned). A Nike footwear customer at day 200 is not at-risk if the median repeat window is 280 days; a skincare customer at day 90 is high-risk if the median repeat window is 45 days.
FR-040 → EPC-05 → PER-03: Churn-risk indicators displayed by segment with customer count, risk level, and relative position to expected repurchase window; drill-down available (read-only customer list).
FR-041 → EPC-05 → System: Contribution margin calculated per customer segment (not product segment). Segments: new customers, returning customers, high-value (top LTV/AOV), at-risk, churned, and custom segments defined by Retention Manager. Margin per segment = (revenue from segment − COGS − shipping − returns cost − attributable acquisition cost) / revenue from segment. Reveals whether high-value returning customers are more profitable than new customers once zero acquisition cost on repeat orders is factored in.
FR-042 → EPC-05 → System: Return/refund data displayed as a retention signal per cohort: return rate correlation with repeat purchase rate shown. Completely separate from operational returns view — no unit cost or logistics data shown here.
FR-043 → EPC-05 → PER-03: Retention Manager has read-only access to acquisition metrics (channel, CAC, first-order AOV) for retention context; no modification capability.
FR-044 → EPC-05 → PER-03: Retention Manager can create and save custom customer segments (e.g., "High-Value: AOV > £500") for repeated use in dashboards and alerts.
FR-045 → EPC-05 → PER-03: Retention Manager can add lifecycle event annotations (e.g., "Flash sale Nov 15") date-linked to cohort curves; visible on dashboard and included in exports.
FR-046 → EPC-05 → PER-03: Retention Manager can export and share cohort health, churn risk, segment performance, and annotations as PDF/CSV and email to selected recipients. Export can be scoped to selected metrics/sections only and is permission-checked for recipient access.


---

### EPC-06 Financial Governance and Margin Intelligence

FR-047 → EPC-06 → PER-04: Finance Controller views contribution margin breakdown by channel, product, and order type — current period vs prior period, actual vs expected, variance highlighted.
FR-048 → EPC-06 → System: Cost driver impact displayed per driver (COGS, shipping, returns processing, discounts, ad spend) as both % of revenue and absolute £ impact on margin; each labeled with source (synced or manual) and last updated/synced time.
FR-049 → EPC-06 → System: Every cost input labeled as synced (source platform + last sync time) or manual (last updated date + owner). Confidence indicator based on recency — not on whether the input is manual or synced. A manually entered value updated today by Finance Controller has equal confidence to a recently synced value. Confidence degrades with time elapsed since last update or sync regardless of source type.
FR-050 → EPC-06 → PER-04: Cost input update interface supports tiered/banded inputs, not single flat values. Shipping costs configurable by weight tier (e.g., 0–0.5kg, 0.5–1kg, 1–2kg) and destination zone (domestic, EU, international). Tax-related costs in scope for Phase 1 are: import duties on inbound stock (included in COGS as landed cost), DDP customs on outbound cross-border orders (included in shipping/fulfillment cost band), non-reclaimable VAT on ad spend (included in ad spend cost input), return tax recovery gap (included in return cost calculation). VAT/GST collected from customers is excluded from margin as a pass-through. Full customs/duties modelling per country deferred to Phase 2.
FR-051 → EPC-06 → System: If a cost input change is high-impact (e.g., COGS change on a top-revenue product), system requires explicit confirmation from Finance Controller before propagating the change to live recommendations and simulations; confirmation logged.
FR-052 → EPC-06 → System: System maintains full version history for every cost input from first value captured in AlpMark onward (including any onboarding-imported baseline where provided): prior value, new value, effective date, variance reason tag, approver, timestamp; version history queryable and exportable for audit.
FR-053 → EPC-06 → PER-04: Finance Controller can set contribution margin drift thresholds per channel and per category (not global only); thresholds stored as profiles, effective immediately for next daily calculation.
FR-054 → EPC-06 → System: System calculates margin drift daily per channel/category: (actual margin − expected margin) / expected margin; alert fired with variance reason context if threshold exceeded.
FR-055 → EPC-06 → PER-04: Finance Controller can run a finance-lens simulation adjusting cost inputs (e.g., return rate drops 2%, shipping band increases) and see projected margin impact with upside and downside scenarios; simulation does not affect live metrics.
FR-056 → EPC-06 → PER-04: Finance Controller can restate a historical period under prior vs new cost inputs and view margin delta; restatement used for audit comparison and governance.
FR-057 → EPC-06 → PER-04: Finance Controller can export and share margin breakdown, cost drivers, version history, drift alerts, and decision log as PDF/CSV for leadership/audit use, including email delivery to selected recipients. Export can be scoped to selected sections/metrics only and is permission-checked for recipient access.


---

### EPC-07 Inventory and Operations Intelligence

FR-058 → EPC-07 → PER-05: Operations Manager lands on inventory health dashboard showing status by SKU and category: in-stock, low-stock, stockout risk (with days-to-stockout), overstock, slow-moving; drill-down to individual SKU and warehouse location.
FR-059 → EPC-07 → System: System compares current inventory vs reorder point per SKU; flags low-stock if inventory < reorder point; status updated daily with visual indicator (green/yellow/red).
FR-060 → EPC-07 → System: Stockout risk calculated per SKU: current inventory / average daily sales velocity (rolling 30-day window); days-to-stockout shown; alert threshold configurable per SKU/category; confidence lower if velocity is volatile.
FR-061 → EPC-07 → System: Overstock detection uses SKU-specific velocity and weeks-of-cover calculation, not a flat multiplier. System calculates average daily/weekly sales velocity per SKU from rolling 90-day historical data. Overstock flagged when current inventory exceeds a configurable weeks-of-cover threshold per SKU or category (e.g., 12 weeks for fast-moving basics, 24 weeks for occasion/seasonal wear). Seasonal context applied: velocity compared against same-period prior year to avoid false overstock flags during expected low-demand seasons (e.g., hoodies in summer). Threshold configurable per category by Operations Manager.
FR-062 → EPC-07 → System: Slow-moving detection requires all of the following to be true before flagging: no sales in > 30 days AND units on hand exceed a configurable minimum quantity threshold AND those units represent more than a configurable weeks-of-cover threshold at current velocity AND capital tied up (units × landed cost) exceeds a configurable tenant-base-currency exposure threshold (e.g., INR, GBP, USD). All thresholds configurable per category. A single unit sitting in a warehouse does not trigger a slow-moving flag.
FR-063 → EPC-07 → PER-05: Where inventory data per warehouse location is available from connected source, Operations Manager sees inventory health per location; falls back to aggregate view if location data unavailable; drill-down to potential stock transfers.
FR-064 → EPC-07 → System: Stockout impact estimated per SKU: lost revenue = estimated daily sales velocity × days-to-restock; repeat purchase risk estimated from historical cohort data showing churn correlation with stockout experience.
FR-065 → EPC-07 → System: Fulfillment and logistics cost impact on contribution margin calculated daily per SKU and category; includes inbound, outbound, storage, and returns logistics costs.
FR-066 → EPC-07 → PER-05: Operational returns view shows return rate, return cost per unit, total return cost burden, and top return-driving SKUs/categories. Completely separate from retention cohort return signal — no repeat purchase or customer cohort data shown here.
FR-067 → EPC-07 → System: Operational anomaly detection auto-fires without pre-configuration: stockout cluster (multiple SKUs entering stockout risk within same period), return spike (return rate 2×+ normal for a SKU/category), shipping cost spike (fulfillment cost per order increases significantly vs 30-day average); alert includes affected SKUs and estimated margin impact.
FR-068 → EPC-07 → PER-05: Operations Manager can add context annotations (e.g., "Supplier delay — lead time +14 days", "Warehouse capacity reduced 20%") date-linked to inventory events; visible on dashboard and in reports.
FR-069 → EPC-07 → System: After an approved operational decision is externally implemented, AlpMark tracks outcome via synced inventory and order data: did inventory recover, did stockout avoid, did repeat purchases stabilise; evidence marker shows what changed, data source, and sync timestamp.
FR-070 → EPC-07 → PER-05: Operations Manager can export and share inventory health, risk alerts, decisions, annotations, and observed outcomes as PDF/CSV and email to selected recipients. Export can be scoped to selected sections/metrics only and is permission-checked for recipient access.


---

### EPC-08 Recommendation and Decision Engine

FR-071 → EPC-08 → System: System generates recommendations automatically from analytics signals (stockout risk, margin drift, churn risk, channel underperformance, overstock, slow-moving inventory). Each recommendation includes: affected area, what the signal is, why it matters (estimated £ impact), what action is suggested, confidence level, and data freshness indicator. AlpMark does not execute any action — recommendation only.
FR-072 → EPC-08 → System: Every recommendation is assigned a unique ID and enters the lifecycle: New → Reviewed → Approved → Rejected → Implemented (externally confirmed) → Outcome Observed. Status is updated by the responsible persona; each status change is timestamped and logged.
FR-073 → EPC-08 → PER-01/02/03/04/05: Responsible persona can approve a recommendation with a free-text rationale (optional) or reject it with a mandatory reason code (e.g., "Not feasible", "Already planned", "Disagree with signal", "Deferred", "Out of scope"). Approval and rejection are logged with persona ID, timestamp, and reason.
FR-074 → EPC-08 → System: Phase 1 — Pattern-aware suppression. When a recommendation type is rejected by the same brand N times (configurable threshold, default 3) with the same reason code, the system automatically suppresses that recommendation type for a configurable suppression window (default 30 days) and flags it as "Previously declined — suppressed until [date]." Brand Admin can override suppression at any time. Suppression log is visible and auditable. Phase 2+ — Feedback-loop learning: system reweights recommendation generation using aggregate approve/reject signals across personas and brands via ML pipeline (deferred, out of scope for Phase 1).
FR-075 → EPC-08 → PER-01/02: Brand Admin and Executive Owner can delegate recommendation approval authority for a specific domain (e.g., "Inventory decisions delegated to Operations Manager") with a date range; delegation is logged; delegated persona receives notification; Brand Admin can revoke delegation at any time.
FR-076 → EPC-08 → System: Implementation gap detection — if a recommendation reaches "Approved" status and no "Implemented" confirmation is received within a configurable window (default 14 days), system surfaces a "Not yet implemented" flag to the approving persona; escalation notification sent if gap exceeds a second configurable threshold (default 30 days).
FR-077 → EPC-08 → System: Once a recommendation is marked "Implemented," outcome tracking begins. System monitors the relevant metric (e.g., inventory level recovered, margin improved, churn rate stabilised) via synced data. After a configurable observation window (default 30 days post-implementation), system generates an outcome summary: metric before, metric after, estimated vs actual impact, data source, sync timestamp.
FR-078 → EPC-08 → PER-01/02/03/04/05: Persona can view their full recommendation history filtered by status, domain, date range, and impact size; can compare estimated impact at time of recommendation vs observed outcome post-implementation.
FR-079 → EPC-08 → System: Recommendation confidence is reduced (and warning shown) if underlying data is stale (>7 days since last sync) at the time of generation; if data is >30 days old, recommendation is withheld and a "Insufficient data freshness" notice shown instead.
FR-080 → EPC-08 → PER-01/02: Brand Admin and Executive Owner can export and share the decision log as PDF/CSV for governance and audit use, with option for full log or scoped view by status/domain/date/metric and email delivery to selected recipients. All shared exports are permission-checked for recipient access.


---

### EPC-09 Simulation Engine

FR-081 → EPC-09 → System: System provides a simulation workspace where personas can test planned decisions before external implementation; simulation results never change live KPI values or recommendation status.
FR-082 → EPC-09 → PER-02: Growth and Performance Manager can simulate budget reallocation across channels/campaign groups and see projected impact on CAC, ROAS, new customer volume, contribution margin, and payback period.
FR-083 → EPC-09 → PER-03: Retention and CRM Manager can simulate retention interventions (offer level, audience segment, send timing, expected response rate) and see projected repeat purchase rate, cohort revenue, and retention margin impact.
FR-084 → EPC-09 → PER-04: Finance Controller can simulate changes in cost inputs (shipping bands, return cost, platform fees, ad VAT, duties assumptions for Phase 1 treatment) and see projected gross margin and contribution margin movement.
FR-085 → EPC-09 → PER-05: Operations Manager can simulate reorder timing, reorder quantity, and lead-time scenarios and see projected stockout risk, overstock risk, weeks-of-cover, and capital tied up.
FR-086 → EPC-09 → PER-01: Executive Owner can run strategic what-if scenarios combining pricing, channel mix, and demand assumptions and see consolidated projected business impact.
FR-087 → EPC-09 → System: Every simulation must show at least three scenarios: baseline (no change), upside, and downside. Downside is mandatory and cannot be hidden.
FR-088 → EPC-09 → System: Side-by-side comparison view shows key metric deltas for each scenario with absolute value and percentage change; includes data freshness and confidence level per metric.
FR-089 → EPC-09 → System: Simulation confidence reflects input quality and recency; if a required input is missing or stale, system shows warning and reduced confidence instead of blocking all output unless minimum required inputs are absent.
FR-090 → EPC-09 → PER-01/02/03/04/05: Persona can save named simulation scenarios, revisit them later, and compare old vs updated outcomes after fresh data sync.
FR-091 → EPC-09 → System: Simulation output export and sharing available as PDF/CSV with assumptions, scenario values, projected impacts, confidence notes, and run timestamp, with optional email delivery to selected recipients. Export can be scoped to selected scenarios/metrics only and is permission-checked for recipient access.

---

### EPC-10 Support and Diagnostics Tooling

FR-092 → EPC-10 → PER-08: Support/Admin Operator sees ticket queue with status, priority, tenant name, issue type, created time, and assigned owner.
FR-093 → EPC-10 → PER-08: Support/Admin Operator can assign/reassign ticket owner and set due date; assignment changes are logged with timestamp and actor.
FR-094 → EPC-10 → PER-08: Support/Admin Operator can request read-only tenant access from an active support ticket; access is scoped only to that tenant and ticket context.
FR-095 → EPC-10 → System: Tenant diagnostic view includes integration status, last successful sync timestamps per source, recent sync failures, token health state, alert history, and recommendation processing state.
FR-096 → EPC-10 → PER-08: Support/Admin Operator can trigger manual re-sync per data source for the selected tenant; system records trigger time, initiator, result, and any error details.
FR-097 → EPC-10 → PER-08: Elevated support access requires explicit justification and approval policy check; read/write elevated actions are blocked by default in Phase 1 except approved operational support actions.
FR-098 → EPC-10 → System: Any granted support access is time-limited with configurable expiry (default 8 hours) and automatic revocation on expiry.
FR-099 → EPC-10 → PER-08: Support/Admin Operator can add internal support notes to a ticket; notes are timestamped and visible to authorized support roles only.
FR-100 → EPC-10 → PER-08: Support/Admin Operator can record resolution summary with root cause category, fix applied, and prevention note before closure.
FR-101 → EPC-10 → System: Ticket cannot be closed without mandatory resolution fields (root cause, action taken, outcome state).
FR-102 → EPC-10 → System: On ticket closure, all temporary tenant access linked to that ticket is revoked immediately.
FR-103 → EPC-10 → PER-08: Support/Admin Operator can escalate unresolved ticket to engineering with severity and impact summary; escalation event is logged.
FR-104 → EPC-10 → System: Full audit log retained for support actions: access requested/granted/revoked, manual sync triggers, ticket state changes, and note/resolution updates.
FR-105 → EPC-10 → System: Support tooling must enforce tenant isolation; support user can only view tenant selected in current ticket context and cannot cross-tenant query in one session.
FR-106 → EPC-10 → System: Financial-sensitive fields (for example detailed cost inputs and margin internals) are masked in support diagnostic mode unless explicit elevated permission is approved and logged.

---

### EPC-11 Notifications and Alert Infrastructure

FR-107 → EPC-11 → PER-01/02/03/04/05: Persona can configure threshold alerts by metric and domain with comparator (>, <, change%), threshold value, and evaluation window.
FR-108 → EPC-11 → PER-01/02/03/04/05: Persona can create notification routing profiles by alert category and severity (in-app only, email, both) and choose recipients by role.
FR-109 → EPC-11 → System: Anomaly detection framework monitors key metrics using rolling baseline and dispersion; default anomaly trigger is 2 standard deviations from baseline with configurable sensitivity by domain.
FR-110 → EPC-11 → System: Threshold alert firing. When configured threshold condition is met, system generates alert and routes it per notification routing rules. Acceptance: 1-hour SLA from breach detection timestamp for alert creation and routing (target: 95% within SLA); payload includes metric value, threshold value, and short trend context over prior comparison window.
FR-111 → EPC-11 → System: Anomaly alert firing. When anomaly condition is met, system generates alert and routes it per notification routing rules. Acceptance: 1-hour SLA from anomaly detection timestamp for alert creation and routing (target: 95% within SLA); payload includes metric, anomaly magnitude (percent vs baseline and score), and plain-language context (for example, "return rate is 3x normal").
FR-112 → EPC-11 → System: KPI drift alerts fire for sustained underperformance vs configured target over configurable duration; alert includes target, actual, drift magnitude, and duration.
FR-113 → EPC-11 → System: Stockout risk alerts fire when projected days-to-stockout falls below configured threshold; alert includes affected SKU/category, days-to-stockout, velocity basis, and confidence.
FR-114 → EPC-11 → System: Churn risk alerts fire when churn risk score or at-risk cohort proportion exceeds configured threshold; alert includes affected segment/cohort and estimated revenue exposure.
FR-115 → EPC-11 → System: Sync failure alerts fire when scheduled sync fails or exceeds max stale interval; alert includes source, last successful sync timestamp, failure reason if available, and likely impact scope.
FR-116 → EPC-11 → System: Token expiry alerts fire before token expiry and on token invalidation; default pre-expiry reminders at 7 days and 1 day; includes reconnect action path for Brand Admin.
FR-117 → EPC-11 → System: Margin drift alerts fire when gross or contribution margin deviates beyond configured threshold; alert includes current margin, baseline/target margin, drift amount, and top contributing drivers if available.
FR-118 → EPC-11 → System: Early performance warning alerts can fire before hard threshold breach using trend projection (for example projected KPI crossing within next N days); marked clearly as warning, not breach.
FR-119 → EPC-11 → System: Operational anomaly alerts fire for stockout clusters, return spikes, and shipping cost spikes. Shipping cost spike is detected when shipping cost per fulfilled order exceeds both a configurable relative threshold vs rolling 30-day baseline (default +30%) and a configurable minimum absolute daily impact in GBP. Acceptance: alert includes affected SKUs/categories/order cohorts, anomaly magnitude (percent and GBP), estimated margin impact, and top contributing drivers (for example zone mix shift, carrier/service mix, weight-band mix, expedite-rate change).
FR-120 → EPC-11 → System: If related source data is stale, alert still routes but includes stale-data warning and lowered confidence indicator.
FR-121 → EPC-11 → System: Every alert payload must include confidence level (high/medium/low) based on data recency and completeness rules.
FR-122 → EPC-11 → PER-01/02: Brand Admin and Executive Owner can configure escalation routing (for example if unacknowledged after X hours, notify additional roles).
FR-123 → EPC-11 → System: In-app notification center shows alert stream with filters (status, type, severity, domain, date), acknowledge/dismiss actions, and deep links to relevant analysis view.
FR-124 → EPC-11 → System: Email notification delivery includes concise summary, impact estimate, and direct link back to in-app alert detail; delivery failures are logged and retry policy applied.
FR-125 → EPC-11 → System: Alert history is immutable and auditable; records creation time, routing destinations, acknowledge/dismiss events, actor, and any rule changes affecting alert behavior.
FR-126 → EPC-08/EPC-09 → PER-01/02/03/04/05: Every recommendation detail view must expose a Simulate action regardless of recommendation status or domain. Clicking Simulate opens the simulation workspace with the recommendation's suggested action and affected parameters pre-populated as the starting scenario inputs. The persona can adjust any assumption before running the simulation. Running a simulation from a recommendation does not change the recommendation's status. The Simulate action is optional — a persona may approve or reject without simulating. Minimum data requirement: at least 90 days of synced historical data must be available for the relevant domain before the simulation can run; if this threshold is not met, the Simulate button is visible but disabled and shows a tooltip stating "Simulation requires 90 days of historical data — [X] days available." Simulations launched from a recommendation are saved against that recommendation's ID so the persona can revisit the simulation alongside the decision record.


---

## Step 7 - User Stories (Approved)

### EPC-01 Tenant and Account Management

US-001 → FR-001: As a Super Admin, I want to create a new tenant with brand name, plan tier, seat limit, and primary contact so that each brand is isolated and tracked from day one.
US-002 → FR-002: As a Brand Admin, I want to activate my account via a secure link and see an onboarding checklist so that I know exactly what to set up next.
US-003 → FR-003: As a Brand Admin, I want the onboarding checklist to auto-update as I complete each step so that I can track setup progress without manual marking.
US-004 → FR-004: As a Brand Admin, I want to invite team members by email and assign roles at invite time so that access is correct from the moment they join.
US-005 → FR-005: As a Brand Admin, I want to view, modify roles for, deactivate, and remove team members so that access stays up to date and every change is auditable.
US-006 → FR-006: As a Brand Admin, I want to manage payment method, seat count, invoices, and plan change requests so that billing stays accurate and plan changes follow approval flow.
US-007 → FR-007: As a Brand Admin, I want to configure which persona receives which alert type and via which channel so that notifications are relevant and routed correctly.
US-008 → FR-008: As a Brand Admin or Super Admin, I want audit logs to be queryable/exportable and shareable by email to authorized recipients so that compliance reviews are easy to run.

### EPC-02 Data Integration and Sync

US-009 → FR-009: As a Brand Admin, I want to connect Shopify, Meta, or Google Ads via OAuth so that data sync starts automatically.
US-010 → FR-010: As a Brand Admin, I want to enter an API key manually where OAuth is unavailable so that non-OAuth platforms can still be connected.
US-011 → FR-011: As a Brand Admin, I want all tokens and API keys stored encrypted so that credentials are never exposed in logs or plaintext.
US-012 → FR-012: As a Brand Admin, I want token expiry alerts at 7 days before and immediately after expiry so that I can re-authorize before sync breaks.
US-013 → FR-013: As a Brand Admin, I want a one-click re-authorize flow so that expired tokens can be renewed quickly and sync resumes.
US-014 → FR-014: As a Brand Admin, I want automated scheduled sync jobs with updated last-sync timestamps so that I know data freshness.
US-015 → FR-015: As a Brand Admin or Support Operator, I want to trigger manual re-sync on demand so that I can refresh stale data quickly.
US-016 → FR-016: As a Brand Admin, I want per-source integration status, last sync time, progress, and actionable errors so that I can diagnose issues.
US-017 → FR-017: As any persona, I want data freshness indicators on metrics/recommendations so that I can judge confidence before acting.

### EPC-03 Executive Intelligence and KPI Tracking

US-018 → FR-018: As an Executive Owner, I want a dashboard with revenue, profit, contribution margin, trend direction, and KPI summary so that I have one trusted business-health view.
US-019 → FR-019: As an Executive Owner, I want to set/update KPI targets with effective dates so that drift calculations use current goals.
US-020 → FR-020: As an Executive Owner, I want daily KPI drift calculation and threshold alerts so that underperformance is identified early.
US-021 → FR-021: As an Executive Owner, I want alerts ranked by impact score so that I focus on the highest financial risk first.
US-022 → FR-022: As an Executive Owner, I want cross-team roll-up with drill-down so that I can review Growth, Retention, Finance, and Ops in one place.
US-023 → FR-023: As an Executive Owner, I want to delegate recommendation approval by recommendation type so that decisions continue when I am unavailable.
US-024 → FR-024: As an Executive Owner, I want stale-data warning before recommendations so that I can decide whether to proceed with caveats.

### EPC-04 Channel and Acquisition Performance

US-025 → FR-025: As a Growth Manager, I want spend, ROAS, CAC, payback, and trends by channel with campaign drill-down so that I can manage acquisition performance.
US-026 → FR-026: As a Growth Manager, I want ROAS calculated daily per channel with confidence indicator so that performance comparisons are reliable.
US-027 → FR-027: As a Growth Manager, I want CAC calculated daily per channel with confidence indicator so that I can monitor efficiency.
US-028 → FR-028: As a Growth Manager, I want payback period with upside/downside scenarios so that budget decisions include risk.
US-029 → FR-029: As a Growth Manager, I want blended and channel contribution margin updated daily so that I see profitability beyond top-line metrics.
US-030 → FR-030: As a Growth Manager, I want early warning alerts for ROAS/CAC threshold breaches so that I can intervene before margin damage increases.
US-031 → FR-031: As a Growth Manager, I want channel-specific alert thresholds so that alerts reflect channel context.
US-032 → FR-032: As a Growth Manager, I want to save custom analysis views for quick recall and team reuse.
US-033 → FR-033: As a Growth Manager, I want timestamped annotations on analysis views so that context is preserved.
US-034 → FR-034: As a Growth Manager, I want to export and email scoped decision summaries (for example ROAS-only) to selected recipients so that each teammate receives only relevant metrics.

### EPC-05 Retention and Cohort Analytics

US-035 → FR-035: As a Retention Manager, I want repeat purchase rate calculated daily with trend so that retention health changes are visible early.
US-036 → FR-036: As a Retention Manager, I want monthly cohort retention curves updated daily so that I can track behavior over time.
US-037 → FR-037: As a Retention Manager, I want side-by-side cohort comparison with overlay and differences so that I can identify what is improving or degrading.
US-038 → FR-038: As a Retention Manager, I want lifecycle funnel conversion/drop-off visibility so that I can focus interventions at the weakest stage.
US-039 → FR-039: As a Retention Manager, I want churn risk based on brand-specific repurchase cadence so that flags match real customer behavior for my brand.
US-040 → FR-040: As a Retention Manager, I want churn indicators by segment with customer count/risk level so that I can prioritize interventions.
US-041 → FR-041: As a Retention Manager, I want contribution margin by customer segment (not product segment) so that I understand segment profitability accurately.
US-042 → FR-042: As a Retention Manager, I want return/refund shown as a retention signal only, separate from operational returns view, so that analytical contexts stay clean.
US-043 → FR-043: As a Retention Manager, I want read-only acquisition metrics for context so that I can analyze without changing growth settings.
US-044 → FR-044: As a Retention Manager, I want to create/save custom customer segments so that segmentation is reusable.
US-045 → FR-045: As a Retention Manager, I want lifecycle event annotations on cohort curves so that business events can be correlated with retention shifts.
US-046 → FR-046: As a Retention Manager, I want to export and email scoped cohort reports to selected recipients so that each audience receives only relevant sections.

### EPC-06 Financial Governance and Margin Intelligence

US-047 → FR-047: As a Finance Controller, I want contribution margin breakdown by channel/product/order type with variance highlights so that I can identify margin leakage.
US-048 → FR-048: As a Finance Controller, I want cost-driver impact shown as percent and absolute amount with source/update time so that I can prioritize highest-impact drivers.
US-049 → FR-049: As a Finance Controller, I want confidence based on recency (not manual vs synced source type) so that fresh manual values are treated fairly.
US-050 → FR-050: As a Finance Controller, I want tiered cost input capture (shipping bands/zones and in-scope tax costs) so that margin calculations reflect real commercial structure.
US-051 → FR-051: As a Finance Controller, I want explicit confirmation for high-impact cost changes before they influence live recommendations/simulations so that accidental updates are prevented.
US-052 → FR-052: As a Finance Controller, I want full version history for each cost input from first value captured in AlpMark onward (including onboarding baseline where provided) so that audit tracing is complete and unambiguous.
US-053 → FR-053: As a Finance Controller, I want per-channel and per-category margin drift thresholds so that monitoring sensitivity matches business context.
US-054 → FR-054: As a Finance Controller, I want daily margin drift calculations with variance reason context so that emerging issues are actionable.
US-055 → FR-055: As a Finance Controller, I want finance-lens simulations with upside/downside so that I can test decisions without affecting live metrics.
US-056 → FR-056: As a Finance Controller, I want to restate historical periods under old/new costs so that I can compare and explain variance for governance.
US-057 → FR-057: As a Finance Controller, I want to export and email scoped finance reports to selected recipients so that each stakeholder gets only the sections they need.

### EPC-07 Inventory and Operations Intelligence

US-058 → FR-058: As an Operations Manager, I want inventory health by SKU/category with drill-down so that risks are visible and actionable.
US-059 → FR-059: As an Operations Manager, I want low-stock flags based on reorder point so that replenishment action can start before stockout.
US-060 → FR-060: As an Operations Manager, I want days-to-stockout from rolling velocity so that urgency is quantified.
US-061 → FR-061: As an Operations Manager, I want overstock logic to use SKU velocity, configurable weeks-of-cover, and seasonal context so that false positives are reduced.
US-062 → FR-062: As an Operations Manager, I want slow-moving detection to require all four conditions and use tenant base currency exposure thresholds (for example INR/GBP/USD) so that noise is reduced and thresholds are market-appropriate.
US-063 → FR-063: As an Operations Manager, I want location-level inventory health where available so that transfer opportunities can be identified.
US-064 → FR-064: As an Operations Manager, I want stockout impact estimation in revenue and repeat-risk terms so that prioritization reflects business impact.
US-065 → FR-065: As an Operations Manager, I want logistics cost impact on contribution margin per SKU/category so that operational costs are visible in profitability decisions.
US-066 → FR-066: As an Operations Manager, I want operational returns analytics separate from retention views so that operational and lifecycle decisions remain distinct.
US-067 → FR-067: As an Operations Manager, I want operational anomaly alerts auto-detected so that non-obvious risk clusters are surfaced early.
US-068 → FR-068: As an Operations Manager, I want date-linked operational annotations so that context is retained in dashboards and reports.
US-069 → FR-069: As an Operations Manager, I want post-implementation outcome tracking so that decision effectiveness is measurable.
US-070 → FR-070: As an Operations Manager, I want to export and email scoped operational reports so that relevant teams receive targeted information.

### EPC-08 Recommendation and Decision Engine

US-071 → FR-071: As any decision persona, I want recommendations generated from analytics signals with impact, confidence, and freshness context so that actions are informed and prioritized.
US-072 → FR-072: As any decision persona, I want every recommendation tracked through a full lifecycle with timestamps so that accountability is clear.
US-073 → FR-073: As any decision persona, I want approval with optional rationale and rejection with mandatory reason code so that decisions are governed and auditable.
US-074 → FR-074: As a Brand Admin, I want repeated rejected recommendation types suppressed temporarily (with override) so that recommendation noise is reduced without losing control.
US-075 → FR-075: As a Brand Admin or Executive Owner, I want to delegate approval authority by domain/time window so that governance continues smoothly.
US-076 → FR-076: As an approving persona, I want implementation-gap detection and escalation so that approved decisions are not left unexecuted.
US-077 → FR-077: As any decision persona, I want outcome summaries after implementation windows so that estimated vs actual impact can be compared.
US-078 → FR-078: As any decision persona, I want full recommendation history filters and impact comparison so that performance learning is possible.
US-079 → FR-079: As any decision persona, I want stale-data based confidence reduction/withholding so that low-quality recommendations are controlled.
US-080 → FR-080: As a Brand Admin or Executive Owner, I want full or scoped decision-log export/email sharing with permission checks so that governance reporting can be tailored by audience.

### EPC-09 Simulation Engine

US-081 → FR-081: As any persona, I want simulation workspace outputs to remain non-persistent to live KPIs/recommendations so that experimentation is safe.
US-082 → FR-082: As a Growth Manager, I want channel budget simulations with CAC/ROAS/new-customer/payback/contribution outputs so that spend decisions are evidence-based.
US-083 → FR-083: As a Retention Manager, I want retention intervention simulations with expected response/timing/segment effects so that campaign plans are validated before launch.
US-084 → FR-084: As a Finance Controller, I want cost-input simulations including tax-cost assumptions in scope so that financial scenario quality is high.
US-085 → FR-085: As an Operations Manager, I want reorder timing/quantity/lead-time simulations so that inventory risk can be balanced against capital tie-up.
US-086 → FR-086: As an Executive Owner, I want strategic what-if simulations across pricing/channel mix/demand so that high-level planning is grounded in modeled outcomes.
US-087 → FR-087: As any simulator user, I want mandatory baseline/upside/downside scenarios so that downside risk is never hidden.
US-088 → FR-088: As any simulator user, I want side-by-side metric deltas with confidence/freshness context so that scenario comparison is clear.
US-089 → FR-089: As any simulator user, I want warnings and reduced confidence when inputs are stale/missing so that assumptions are explicit.
US-090 → FR-090: As any simulator user, I want named scenarios saved/revisited/compared after fresh syncs so that iterative planning is possible.
US-091 → FR-091: As any simulator user, I want to export and email scoped simulation outputs (selected scenarios/metrics) so that collaborators receive only relevant scenario details.

### EPC-10 Support and Diagnostics Tooling

US-092 → FR-092: As a Support/Admin Operator, I want ticket queue visibility by status/priority/tenant/owner so that triage is efficient.
US-093 → FR-093: As a Support/Admin Operator, I want assignment and due-date management with change logs so that ownership is clear.
US-094 → FR-094: As a Support/Admin Operator, I want read-only tenant access requests scoped to active ticket context so that diagnostics remain secure.
US-095 → FR-095: As a Support/Admin Operator, I want tenant diagnostics (integration/sync/token/alerts/recommendation state) so that issue root-cause analysis is faster.
US-096 → FR-096: As a Support/Admin Operator, I want manual re-sync triggers with initiator/result/error logs so that recovery actions are auditable.
US-097 → FR-097: As a Support/Admin Operator, I want elevated access behind justification and approval checks so that privileged actions are controlled.
US-098 → FR-098: As a Support/Admin Operator, I want time-limited access grants with auto-revocation so that temporary access does not persist.
US-099 → FR-099: As a Support/Admin Operator, I want internal timestamped support notes so that investigation context is preserved.
US-100 → FR-100: As a Support/Admin Operator, I want mandatory resolution summary capture before closure so that outcomes are documented.
US-101 → FR-101: As a Support/Admin Operator, I want closure blocked if mandatory resolution fields are missing so that ticket quality is enforced.
US-102 → FR-102: As a Support/Admin Operator, I want all temporary access revoked on closure so that security boundaries are restored immediately.
US-103 → FR-103: As a Support/Admin Operator, I want escalation to engineering with severity/impact logging so that unresolved high-impact issues are routed correctly.
US-104 → FR-104: As a Support/Admin Operator, I want complete audit logs of support actions so that compliance and troubleshooting are supported.
US-105 → FR-105: As a Support/Admin Operator, I want strict tenant isolation in support sessions so that cross-tenant data exposure is impossible.
US-106 → FR-106: As a Support/Admin Operator, I want financial-sensitive fields masked unless explicitly approved for elevated access so that sensitive data stays protected.

### EPC-11 Notifications and Alert Infrastructure

US-107 → FR-107: As any persona, I want configurable threshold alerts by metric/domain/comparator/window so that alerting matches my operating context.
US-108 → FR-108: As any persona, I want routing profiles by alert category/severity/channel/role so that alerts reach the right people.
US-109 → FR-109: As any persona, I want anomaly detection from rolling baseline with configurable sensitivity so that outliers are surfaced without manual setup.
US-110 → FR-110: As any persona, I want threshold alerts fired/routed within 1-hour SLA with metric/threshold/trend payload so that threshold breaches are actionable quickly.
US-111 → FR-111: As any persona, I want anomaly alerts fired/routed within 1-hour SLA with magnitude and plain-language context so that severity is clear immediately.
US-112 → FR-112: As any persona, I want KPI drift alerts with target/actual/drift/duration details so that sustained underperformance is explicit.
US-113 → FR-113: As any persona responsible for inventory, I want stockout-risk alerts with days-to-stockout and confidence so that remediation can be prioritized.
US-114 → FR-114: As any persona responsible for retention, I want churn-risk alerts with affected segment and revenue exposure so that intervention urgency is clear.
US-115 → FR-115: As any persona dependent on data freshness, I want sync-failure alerts with source/last success/reason/impact scope so that data risks can be addressed quickly.
US-116 → FR-116: As a Brand Admin, I want token expiry pre-alerts and invalidation alerts with reconnect path so that integrations remain healthy.
US-117 → FR-117: As a Finance Controller, I want margin-drift alerts with driver context so that root causes are easier to identify.
US-118 → FR-118: As any persona, I want early trend-based warning alerts labeled as warnings (not breaches) so that preemptive action can be taken.
US-119 → FR-119: As an Operations Manager, I want operational anomaly alerts including defined shipping-cost spike logic with magnitude/impact/driver details so that response is focused.
US-120 → FR-120: As any persona, I want stale-data warning embedded in alerts when source freshness is low so that confidence is calibrated.
US-121 → FR-121: As any persona, I want confidence level in every alert payload so that I can weigh signals appropriately.
US-122 → FR-122: As a Brand Admin or Executive Owner, I want escalation routing for unacknowledged alerts so that unresolved alerts are not ignored.
US-123 → FR-123: As any persona, I want in-app notification center filtering and acknowledge/dismiss workflow with deep links so that alert handling is efficient.
US-124 → FR-124: As any persona, I want email notifications with concise summary, impact estimate, deep link, and delivery retry so that email alert reliability is maintained.
US-125 → FR-125: As governance stakeholders, we want immutable auditable alert history with routing/actions/rule changes so that full alert traceability is preserved.
US-126 → FR-126: As any decision persona, I want a Simulate option on every recommendation so that I can model the expected outcome before deciding to approve or reject, with the recommendation's own parameters pre-filled as the starting point.



---

## Step 8 - Non-Functional Requirements (Approved)

| ID | Owner | Priority | Depends On | Requirement | Simple Meaning | Acceptance Criteria |
|---|---|---|---|---|---|---|
| NFR-001 | Platform Engineering | Must | FR-001 to FR-125 | Multi-tenant isolation at application, data, and access layers. | One brand can never see another brand's data. | Zero cross-tenant reads/writes in automated tests; tenant boundary checks on all data paths. |
| NFR-002 | Security | Must | FR-009 to FR-017 | Secrets/credentials encrypted at rest and never logged in plaintext. | API keys/tokens are always hidden and protected. | Secret/log scans show zero plaintext credentials. |
| NFR-003 | Security | Must | FR-001 to FR-125 | Data in transit must use TLS 1.2+ with secure transport config. | All traffic is securely encrypted over the internet. | External scan reports no critical transport-security issues. |
| NFR-004 | Security | Must | FR-001 to FR-008, FR-092 to FR-106 | RBAC enforced for every UI action and API endpoint. | Users can only do what their role allows. | Unauthorized-role tests deny access in 100% restricted cases. |
| NFR-005 | Security/Governance | Must | FR-008, FR-052, FR-104, FR-125 | Audit logs immutable, timestamped, and queryable per tenant. | Activity history cannot be tampered with. | Standard roles cannot edit/delete logs; tenant/date query-export works. |
| NFR-006 | Reliability | Must | FR-014, FR-115 | Scheduled sync service availability >= 99.5% monthly. | Sync should almost always be running. | Monthly uptime report shows >= 99.5%. |
| NFR-007 | Reliability | Must | FR-014 to FR-017 | Automatic sync retries with capped backoff and visible terminal failure state. | Failed syncs retry automatically, then fail clearly if needed. | Failed jobs retry per policy; final failure reason visible. |
| NFR-008 | Performance | Must | FR-018 to FR-070, FR-123 | Core dashboard load time P95 <= 3s after auth (standard date ranges). | Dashboards should feel fast for most users. | Monitoring confirms P95 <= 3s for core dashboards. |
| NFR-009 | Performance | Must | FR-110, FR-111 | Alert pipeline meets 1-hour SLA for 95% of eligible alerts. | Alerts should arrive quickly enough to act on. | Monthly report shows >= 95% routed within 1 hour from detection. |
| NFR-010 | Performance | Should | FR-034, FR-046, FR-057, FR-070, FR-080, FR-091 | Standard PDF/CSV exports complete quickly with status feedback. | Reports should generate quickly and show progress. | 90% complete within 2 minutes; progress/failure visible. |
| NFR-011 | Scalability | Must | FR-001 to FR-125 | Scale to target tenant/user concurrency without SLA breach. | More customers/users should not slow or break the system. | Load test preserves NFR-008 and NFR-009 thresholds. |
| NFR-012 | Data Quality | Must | FR-017, FR-024, FR-079, FR-120, FR-121 | Freshness/confidence labels deterministic across all surfaces. | Same data should show same confidence everywhere. | Same data state yields same label in all views. |
| NFR-013 | Data Governance | Must | FR-049, FR-052 | Cost-input lineage complete from first value captured in AlpMark onward. | Every cost change has full history. | Full chain available: value, actor, timestamp, reason, effective date. |
| NFR-014 | Business Constraint | Must | FR-071 to FR-091 | AlpMark remains decision-intelligence only; no external action execution. | AlpMark recommends, but never performs external actions. | No production endpoint performs external mutating actions. |
| NFR-015 | Availability/DR | Must | FR-001 to FR-125 | Backup/recovery must meet RPO/RTO targets. | If something breaks, data recovery is predictable and timely. | Daily encrypted backups; RPO <= 24h and RTO <= 8h validated. |
| NFR-016 | Privacy/Compliance | Must | FR-001 to FR-125 | Tenant data handling must support privacy obligations. | Privacy requests can be handled properly with records. | Governed export/delete workflow executable with audit trail. |
| NFR-017 | Observability | Must | FR-014 to FR-125 | Centralized logs, metrics, traces, and service alerting for critical services. | System health is visible; issues are detectable early. | Health dashboards and on-call alerts active for critical services. |
| NFR-018 | Operability | Should | FR-092 to FR-106 | Support diagnostics should reduce MTTR for common incidents. | Support team should troubleshoot faster. | Median diagnostic time improves to agreed target. |
| NFR-019 | Usability | Should | FR-018 to FR-125 | UI clear and task-oriented for non-technical business users. | Business users can use it without heavy training. | Persona UAT shows >= 80% unassisted completion on core flows. |
| NFR-020 | Accessibility | Must | FR-018 to FR-125 | Core workflows must meet WCAG 2.1 AA. | Product should be usable for people with accessibility needs. | No critical WCAG 2.1 AA violations on primary flows. |
| NFR-021 | Compatibility | Should | FR-018 to FR-125 | Support current + previous major versions of Chrome/Safari/Edge (desktop). | Works reliably on major browsers customers use. | Cross-browser regression passes supported matrix. |
| NFR-022 | Localization | Should | FR-050, FR-062, FR-119 | Monetary/number formatting follows tenant base currency and locale. | INR/GBP/USD and number formats display correctly per tenant. | UI/exports consistently use tenant-configured currency/locale. |
| NFR-023 | Notification Delivery | Should | FR-108, FR-124 | Email delivery monitored; transient failures retried automatically. | Email alerts should not fail silently. | Delivery/retry metrics visible; retries execute per policy. |
| NFR-024 | Security/Access Lifecycle | Must | FR-094, FR-097, FR-098, FR-102 | Temporary support access auto-expires and revokes on ticket closure. | Support access is temporary and cleaned up automatically. | Access audits show no temporary sessions after expiry/closure. |


---

## Step 9 - Scope and Priority (Approved)

### 9.1 Scope Boundary

**In scope for the current product definition**
- EPC-01 to EPC-11
- FR-001 to FR-125
- NFR-001 to NFR-024

This means the product definition covers the full end-to-end AlpMark platform required to onboard a tenant, connect data, generate intelligence, route alerts, log decisions, simulate outcomes, and support live customers.

**Explicitly out of scope for the current build**
These are intentionally excluded from current build scope and may be considered later in Step 12 (Phase Plan).

| Item | Status | Reason |
|---|---|---|
| Full per-country customs and duties modelling | Out of scope | Current scope includes tax treatment required for landed cost and margin logic, but not full destination-country customs rule engines. |
| ML-based adaptive recommendation learning and alert suppression | Out of scope | Current scope supports rule-based suppression and deterministic analytics. ML feedback loops need post-launch data and added governance. |
| Mobile native app (iOS / Android) | Out of scope | Responsive web only in current scope. |
| Marketplace integrations beyond defined source list | Out of scope | No Amazon, eBay, Flipkart, or similar marketplace connectors in current scope. |
| Accounting / ERP integrations beyond current defined sources | Out of scope | No QuickBooks, Xero, NetSuite, SAP, or equivalent finance-system connectors in current scope. |
| B2B / wholesale analytics | Out of scope | Current product scope is D2C physical-product brands only. |
| Predictive ML recommendation generation | Out of scope | Current recommendations are driven by defined signals, thresholds, anomaly rules, and deterministic business logic. |

**Important boundary note**
- Step 9 defines what is in scope, out of scope, and how work is prioritised.
- Step 9 does not decide Phase 1 / Phase 2 release cuts.
- Any existing "Phase 1" or "Phase 2" wording in prior FRs remains provisional and will be formalised only in Step 12.

### 9.2 Prioritisation Framework

MoSCoW is used at three levels:
- Epic level
- FR level
- NFR level

| Label | Meaning |
|---|---|
| Must | Required for AlpMark to be viable, trustworthy, and launchable. No acceptable workaround. |
| Should | Important and high value, but AlpMark still functions without it in the first launchable release. |
| Could | Useful enhancement, but deferrable with low launch risk. |
| Won't (for now) | Explicitly excluded from the current build scope. |

**Priority inheritance rule**
- If an epic is Must, its FRs default to Must unless specifically downgraded to Should or Could.
- If an epic is Should, its FRs default to Should unless specifically elevated.

### 9.3 Epic Priority

| Epic ID | Epic Name | Priority | Rationale |
|---|---|---|---|
| EPC-01 | Tenant and Account Management | Must | Required to create tenants, control access, manage users, and support billing/governance. |
| EPC-02 | Data Integration and Sync | Must | Without connected and refreshed data, AlpMark cannot produce reliable intelligence. |
| EPC-03 | Executive Intelligence and KPI Tracking | Must | Core value surface for the Executive Owner and primary buyer-level visibility. |
| EPC-04 | Channel and Acquisition Performance | Must | Core daily decision surface for growth teams. |
| EPC-05 | Retention and Cohort Analytics | Must | Core daily decision surface for retention teams. |
| EPC-06 | Financial Governance and Margin Intelligence | Must | Core daily decision surface for finance teams and critical for trust in decisions. |
| EPC-07 | Inventory and Operations Intelligence | Must | Core daily decision surface for operations teams. |
| EPC-08 | Recommendation and Decision Engine | Must | Core product differentiator and the center of decision logging and accountability. |
| EPC-09 | Simulation Engine | Should | High-value differentiator, but AlpMark remains useful and sellable without simulation in the first launchable cut. |
| EPC-10 | Support and Diagnostics Tooling | Must | Required to support live tenants safely and operate the platform. |
| EPC-11 | Notifications and Alert Infrastructure | Must | Cross-cutting dependency needed for alerts, routing, freshness warnings, and trust signals. |

### 9.4 Connector Priority Inside EPC-02

EPC-02 is Must overall, but not every future connector is Must for initial launch.

| Connector / Source Type | Priority | Reason |
|---|---|---|
| Shopify | Must | Core commerce/order data source for D2C brands. |
| Meta Ads | Must | One of the most common paid acquisition sources for the target customer. |
| Google Ads | Must | Core paid acquisition source for the target customer. |
| Manual token/API-key connection where OAuth unavailable | Must | Required to avoid blocking supported sources that lack OAuth. |
| Additional future connectors beyond current source set | Won't for now | Outside current build scope. |

### 9.5 FR Priority Rules

**Default rule**
- All FRs in Must epics are Must unless listed below as exceptions.
- All FRs in EPC-09 are Should by default because EPC-09 is Should.

#### 9.5.1 Must-Epic FRs that are Should
| FR | Epic | Priority | Reason |
|---|---|---|---|
| FR-023 | EPC-03 | Should | Delegation improves governance flexibility, but core dashboard and approval visibility still work without it. |
| FR-032 | EPC-04 | Should | Saved analysis views improve repeat use and collaboration, but core acquisition analytics work without saved views. |
| FR-033 | EPC-04 | Should | Annotations add context, but core performance analysis still works without them. |
| FR-045 | EPC-05 | Should | Lifecycle event annotations are useful context, but not required for baseline cohort and churn analysis. |
| FR-056 | EPC-06 | Should | Historical restatement is valuable for audit and finance review, but core margin management works without it at launch. |
| FR-068 | EPC-07 | Should | Operational annotations help explain events, but inventory intelligence works without them. |
| FR-076 | EPC-08 | Should | Implementation gap detection strengthens governance, but recommendation lifecycle can function without automated gap follow-up. |
| FR-078 | EPC-08 | Should | Rich filtered recommendation history improves review and learning, but recommendation generation and logging still work without full history tooling. |

#### 9.5.2 Must-Epic FRs that are Could
No current Must-epic FRs are rated Could. The remaining non-core items are still important enough to retain at Should.

#### 9.5.3 EPC-09 FR Priority
All FRs under EPC-09 inherit Should by default:

- FR-081
- FR-082
- FR-083
- FR-084
- FR-085
- FR-086
- FR-087
- FR-088
- FR-089
- FR-090
- FR-091

Rationale:
- Simulation adds strong strategic value and differentiation.
- AlpMark’s core proposition still stands without simulation because recommendations, alerts, analytics, governance, and outcome tracking remain intact.

### 9.6 NFR Priority and Launch Dependency

All NFRs remain in scope, but their launch importance is not equal.

#### 9.6.1 Must NFRs for launch
These are co-requisites for launch. A release is not launch-ready unless these are satisfied alongside the dependent FRs.

- NFR-001 Multi-tenant isolation
- NFR-002 Secrets and credential protection
- NFR-003 Secure transport
- NFR-004 RBAC enforcement
- NFR-005 Immutable audit logs
- NFR-006 Sync availability
- NFR-007 Sync retry and failure handling
- NFR-008 Core dashboard performance
- NFR-009 Alert SLA performance
- NFR-011 Scalability within target load
- NFR-012 Consistent freshness/confidence labels
- NFR-013 Cost-input lineage
- NFR-014 Decision-intelligence only boundary
- NFR-015 Backup and recovery
- NFR-016 Privacy/compliance handling
- NFR-017 Observability
- NFR-020 Accessibility on core workflows
- NFR-024 Temporary support access expiry and revocation

#### 9.6.2 Should NFRs
These remain in scope, but are not hard launch blockers if a controlled exception is agreed.

- NFR-010 Export performance
- NFR-018 Support MTTR improvement target
- NFR-019 Usability completion target
- NFR-021 Browser compatibility breadth
- NFR-022 Localization and tenant currency/locale formatting consistency
- NFR-023 Notification delivery monitoring and retry visibility

### 9.7 Launch Readiness Gate

For AlpMark to be considered **launch-ready**, all of the following must be true:

- All Must epics are delivered to agreed acceptance level.
- All Must FRs are implemented and verified.
- All Must NFRs are met or formally exception-approved with compensating controls.
- Tenant isolation, security, auditability, sync reliability, and alert routing are proven in validation.
- AlpMark remains strictly within the decision-intelligence boundary and performs no external mutating actions.
- Support tooling is sufficient to diagnose tenant issues safely in production.

This gives a clear launch bar before Step 12 decides release slicing.

### 9.8 Deferred Items Log

| Deferred Item | Related Reference | Status |
|---|---|---|
| Full customs / duties modelling per country | FR-050 placeholder language | Deferred to Step 12 scheduling |
| ML-based recommendation reweighting / learning | FR-074 placeholder language | Deferred to Step 12 scheduling |
| Native mobile apps | No FR in current scope | Out of scope for current build |
| Marketplace connectors | No FR in current scope | Out of scope for current build |
| Accounting / ERP connectors | No FR in current scope | Out of scope for current build |
| B2B / wholesale analytics | No FR in current scope | Out of scope for current build |
| Predictive ML recommendation generation | No FR in current scope | Out of scope for current build |



## Step 10 - Solution Approach and Trade-offs (Approved)

### 10.1 Purpose

This step chooses the practical delivery approach for AlpMark by comparing credible options and selecting the one that gives the best balance of:
- delivery speed
- build cost
- operating cost
- implementation risk
- supportability
- future scalability
- trust and governance fit

This is not the detailed technical design. That comes in Step 11.

### 10.2 Decision Criteria

| Criterion | What it means for AlpMark |
|---|---|
| Delivery speed | How quickly the first launchable product can be built |
| Build cost | Engineering effort and upfront complexity |
| Operating cost | Hosting, support, maintenance, and operational overhead |
| Delivery risk | Chance of delays, integration fragility, or implementation failure |
| Product fit | How well the approach supports AlpMark's decision-intelligence model |
| Governance fit | How well the approach supports traceability, approvals, audit, and tenant isolation |
| Scalability | Ability to grow with more tenants, users, and data volume |
| Explainability | Ability to clearly justify recommendations and alerts |

### 10.3 Major Approach Decisions

#### SA-001 Product Interaction Model

| Option | Pros | Cons |
|---|---|---|
| Decision-intelligence only | Lower execution risk, clearer governance boundary, easier auditability, safer for launch | Users must still execute actions outside AlpMark |
| Direct execution into external systems | More automation, faster end-user action | Higher compliance risk, more integration fragility, harder rollback, higher support burden |

Chosen approach: Decision-intelligence only

Why chosen:
This is the lowest-risk model and best fits AlpMark's trust-first positioning. It avoids turning the product into an execution platform before governance and operational maturity are proven.

Trade-off accepted:
Less automation in exchange for lower risk and easier control.

#### SA-002 Delivery Surface

| Option | Pros | Cons |
|---|---|---|
| Responsive web app | Lowest build cost, fastest launch, broad role coverage, easiest maintenance | Mobile experience not as strong as native |
| Web + native mobile apps | Better mobile UX | Higher build cost, higher maintenance cost, slower launch |

Chosen approach: Responsive web app only

Why chosen:
All primary personas can use a web product effectively. Native mobile adds cost without being essential to the first launchable version.

Trade-off accepted:
Lower cost and faster delivery over mobile-native convenience.

#### SA-003 Integration Model

| Option | Pros | Cons |
|---|---|---|
| Scheduled sync with manual re-sync | Lower integration complexity, easier support, more predictable operations | Not real-time |
| Real-time event-driven sync everywhere | More immediate data | Much higher complexity, harder debugging, greater third-party dependency risk |

Chosen approach: Scheduled sync with manual re-sync support

Why chosen:
This gives the best balance of implementation cost, reliability, and supportability for a SaaS analytics product.

Trade-off accepted:
Data freshness is slightly lower, so trust indicators must compensate.

#### SA-004 Analytics and Recommendation Logic

| Option | Pros | Cons |
|---|---|---|
| Deterministic rules, formulas, thresholds, anomaly logic | Easier to explain, test, audit, and govern | Less adaptive |
| ML-first recommendation engine | More advanced pattern detection potential | Higher build risk, harder to explain, more governance complexity, needs training data |

Chosen approach: Deterministic logic first

Why chosen:
AlpMark must earn trust before adding black-box intelligence. Deterministic logic is cheaper to build, easier to validate, and more suitable for finance and operations use cases.

Trade-off accepted:
Less sophistication early in exchange for lower delivery risk and higher trust.

#### SA-005 Application Architecture Shape

| Option | Pros | Cons |
|---|---|---|
| Modular monolith / tightly integrated platform | Faster delivery, lower operating cost, easier end-to-end changes, simpler support | Some future scaling boundaries may need refactoring |
| Microservices from the start | Better long-term separation potential | Higher engineering overhead, higher infra cost, more operational complexity, slower delivery |

Chosen approach: Modular monolith or tightly integrated platform first

Why chosen:
At AlpMark's current stage, microservices would raise cost and delivery risk without enough near-term benefit.

Trade-off accepted:
Some future restructuring risk in exchange for faster and cheaper initial delivery.

#### SA-006 Data Trust Handling

| Option | Pros | Cons |
|---|---|---|
| Surface freshness/confidence on all key outputs | More honest and governable, better user trust | More UI and logic complexity |
| Hide trust complexity from users | Cleaner UI | Higher risk of misuse and false confidence |

Chosen approach: Always surface freshness, confidence, and stale-data warnings

Why chosen:
For a decision product, hidden uncertainty is more dangerous than visible complexity.

Trade-off accepted:
Slightly more interface complexity in exchange for better trust and decision quality.

#### SA-007 Simulation Approach

| Option | Pros | Cons |
|---|---|---|
| Separate simulation sandbox | Safe, controlled, no corruption of live metrics | More logic separation required |
| Direct simulation on live state | Simpler conceptually for users | Higher risk of confusion, contamination of live reporting |

Chosen approach: Separate simulation sandbox

Why chosen:
This is the safer option for a decision platform where live KPIs and hypothetical outcomes must never be confused.

Trade-off accepted:
Extra implementation effort in exchange for safer product behavior.

#### SA-008 Support Operating Model

| Option | Pros | Cons |
|---|---|---|
| Built-in scoped support tooling | Safer production support, better auditability, faster diagnosis | More internal tooling to build |
| Ad hoc manual database/support access | Lower upfront tooling effort | High security risk, poor auditability, inconsistent support operations |

Chosen approach: Built-in scoped support tooling

Why chosen:
For a multi-tenant SaaS product, ad hoc support access creates unacceptable security and governance risk.

Trade-off accepted:
More initial build effort in exchange for lower operational risk.

### 10.4 Recommended Overall Solution Approach

Based on cost, risk, and delivery trade-offs, the recommended approach for AlpMark is:
- responsive web application
- modular monolith / tightly integrated platform first
- scheduled sync integrations with manual re-sync support
- deterministic analytics, thresholds, and anomaly detection first
- decision-intelligence only, with no external action execution
- simulation in a separate safe sandbox
- strong trust markers: freshness, confidence, and stale-data warnings
- built-in support tooling with scoped access and auditability

This gives AlpMark the best balance of:
- lower upfront engineering cost
- lower operating complexity
- lower delivery risk
- stronger governance fit
- faster path to launch
- clearer foundation for later scaling

### 10.5 Trade-offs Accepted

| What we gain | What we give up |
|---|---|
| Faster launch | Less automation |
| Lower build cost | Fewer advanced ML capabilities initially |
| Lower support complexity | No real-time system-wide data model |
| Stronger auditability | More manual execution outside AlpMark |
| Simpler operations | Less architectural flexibility in the earliest version |
| Higher trust | Some high-end predictive features deferred |

### 10.6 What Is Explicitly Deferred by This Approach

These are not rejected forever. They are simply not chosen now because cost/risk is too high relative to current value:
- external action execution into third-party systems
- ML-first recommendation generation
- adaptive ML suppression and learning loops
- real-time streaming architecture across all sources
- native mobile apps
- broad connector expansion beyond core sources
- microservices-first platform design

### 10.7 Step 10 Summary

The chosen solution approach for AlpMark is the lowest-risk, highest-control, most supportable route to a launchable decision-intelligence SaaS product.

It prioritizes:
- trust over novelty
- explainability over black-box intelligence
- safe decision support over automation
- delivery speed over architectural ambition
- operational simplicity over premature scale complexity


## Step 11 - Technical Specification

### 11.1 Tech Stack Decisions

#### 11.1.1 Backend Language and Framework
- **Decision: Python + FastAPI**
- Why chosen: Python excels at analytics-heavy logic, deterministic rule evaluation, and future ML integration. FastAPI provides fast async APIs with automatic request validation and OpenAPI documentation.
- Alternatives rejected:
  - Node.js/Express: lacks mature analytics libraries; less suited for data transformation pipelines.
  - Go: faster at runtime but steeper learning curve and smaller ecosystem for rules/analytics.
- Implementation impact: async/await patterns for I/O-bound connectors and workers.

#### 11.1.2 Background Job Queue and Scheduler
- **Decision: Celery + Redis**
- Why chosen: Celery is the Python standard for scheduled and async jobs. Redis provides reliable queue management with simple operations. Proven pattern for connector sync, alerts, and long-running data operations.
- Alternatives rejected:
  - APScheduler alone: limited retry/backoff capabilities.
  - AWS SQS: adds AWS lock-in; Celery + Redis more portable.
- Implementation impact: retry decorators, periodic task scheduling via celery beat.

#### 11.1.3 Primary Database
- **Decision: PostgreSQL**
- Why chosen: Relational integrity for multi-table order/product data. Strong JSON support for flexible metric schemas. Excellent Python support via SQLAlchemy. UUID and JSONB types reduce custom serialization logic.
- Alternatives rejected:
  - MongoDB: loses referential integrity; higher risk for tenant data leakage.
  - MySQL: PostgreSQL's advanced features (JSONB, window functions) valuable for analytics.
- Implementation impact: leverages partial indexes for tenant scoping, native JSON queries.

#### 11.1.4 Tenancy Model and Data Isolation
- **Decision: Shared database, strict tenant_id on every business table**
- Why chosen: Reduces operational complexity (one DB, one backup strategy). Tenant_id enforced at application layer (every query filters by tenant_id) and database layer (row-level security if needed later).
- Alternatives rejected:
  - Separate schema per tenant: higher operational overhead, migration complexity.
  - Separate DB per tenant: doesn't scale cost-effectively for 5–50 pilot tenants.
- Implementation impact: helper functions to inject tenant_id into all queries; integration tests verify no cross-tenant leakage.

#### 11.1.5 ORM and Migrations
- **Decision: SQLAlchemy 2.x + Alembic**
- Why chosen: SQLAlchemy provides explicit control over queries, strong type hints, and clear relationships. Alembic enables safe schema versioning with rollback capability.
- Alternatives rejected:
  - Django ORM: tightly coupled to Django framework; overkill for modular backend.
  - Raw SQL: loses type safety and code reusability.
- Implementation impact: declarative models, automatic type conversion, migration scripts in version control.

#### 11.1.6 API Contract and Versioning
- **Decision: Versioned REST APIs (JSON over HTTP)**
- Why chosen: Clear contracts between frontend and backend. Easy to version and deprecate endpoints. Frontend-agnostic (works with Next.js, mobile later, etc.).
- Alternatives rejected:
  - GraphQL: overkill for current scope; REST sufficient and simpler to operationalize.
  - gRPC: requires significant frontend complexity.
- Implementation impact: all endpoints prefixed `/api/v1/`, response envelope standardization, OpenAPI schema auto-generated by FastAPI.

#### 11.1.7 Authentication and Authorization
- **Decision: Managed OAuth2 provider (Auth0/Clerk) + internal RBAC**
- How it works:
  1. User logs in via Auth0/Clerk; receives JWT token.
  2. Frontend includes JWT in Authorization header.
  3. Backend validates JWT signature and extracts email.
  4. Backend looks up internal user record and role (e.g., "operator", "analyst", "finance").
  5. Every API endpoint enforces role-based permission checks.
- Why chosen: Auth0/Clerk handle login security, MFA, password reset safely. Internal RBAC keeps business permissions in AlpMark codebase under your control.
- Alternatives rejected:
  - In-house auth: risky (password hashing, session management, MFA hard to get right).
  - Keycloak self-hosted: adds ops overhead for pilot.
- Implementation impact: JWT middleware, permission decorators on endpoints, role seeding at tenant creation.

#### 11.1.8 Frontend Framework
- **Decision: Next.js + TypeScript**
- Why chosen: Next.js provides app routing, built-in auth patterns, server-side rendering for SEO. TypeScript catches errors at build time. Strong ecosystem and long-term maintainability.
- Alternatives rejected:
  - React + Vite: requires manual routing setup; fewer integrated features.
  - Vue.js: narrower job market; TypeScript support weaker.
- Implementation impact: file-based routing, API route handlers for backend calls, deployment via Vercel or Docker.

#### 11.1.9 Caching and Temporary Storage
- **Decision: Redis (single component, multiple uses)**
- Uses:
  1. Celery broker (job queue) and result backend.
  2. Session cache for API requests.
  3. Rate limiting per user/tenant.
- Why chosen: Single operational component reduces setup and monitoring burden. Redis is mature and widely supported.
- Implementation impact: connection pooling, TTL policies for cache expiry, clear key namespacing by tenant.

#### 11.1.10 File and Export Storage
- **Decision: S3-compatible object storage (e.g., AWS S3)**
- Use cases:
  1. Exported metrics (CSV, JSON) with time-limited signed URLs.
  2. Raw connector payloads for audit and replay.
  3. Shared export links with permission checks.
- Why chosen: Durable, scalable, pay-per-use. S3-compatible API allows future multi-cloud flexibility.
- Implementation impact: presigned URLs for temporary access, lifecycle policies for data retention.

#### 11.1.11 Observability Stack
- **Decision: OpenTelemetry + Prometheus + Grafana + Sentry**
- What each does:
  1. **OpenTelemetry**: collects traces, metrics, logs from application code. Sends to collectors.
  2. **Prometheus**: receives and stores metrics (latency, error rates, queue depth). Time-series DB.
  3. **Grafana**: visualizes Prometheus data as dashboards. Alerts on threshold breaches.
  4. **Sentry**: captures exceptions and stack traces. Groups similar errors, tracks error rates over time.
- Why chosen: Standard observability stack. Prometheus and Grafana are open-source (low cost). Sentry free tier sufficient for pilot. OpenTelemetry is portable (not locked to one vendor).
- Implementation impact: instrument FastAPI with ASGI middleware, log structured JSON, emit custom metrics for recommendation generation.

#### 11.1.12 Infrastructure and Deployment
- **Decision: Containerized on AWS (ECS Fargate, RDS, ElastiCache)**
- Components:
  1. **Docker image**: FastAPI app + Celery worker in separate containers, same image.
  2. **ECS Fargate**: serverless container orchestration (no EC2 instances to manage).
  3. **RDS PostgreSQL**: managed database with automatic backups and failover.
  4. **ElastiCache Redis**: managed Redis cluster.
- Why chosen: Managed services reduce day-1 ops burden. Fargate auto-scales containers. RDS and ElastiCache handle upgrades, backups, monitoring.
- Alternatives rejected:
  - Kubernetes: overkill for single-founder pilot; higher operational complexity.
  - Bare EC2: requires manual patching, scaling.
- Implementation impact: Dockerfile for app, Terraform/CloudFormation for infra-as-code, CI/CD pipeline deploys on push to main.

#### 11.1.13 Testing and Code Quality
- **Decision: pytest + pytest-asyncio + httpx + Playwright**
- Testing layers:
  1. **Unit tests** (pytest): rule evaluation, state transitions, currency logic.
  2. **Integration tests** (pytest + httpx): API endpoints, tenant isolation, RBAC.
  3. **End-to-end tests** (Playwright): recommendation flow from generation to approval in UI.
  4. **Contract tests**: connector adapters validate schema against source API.
- Code quality gates:
  1. **ruff**: fast linter (style, imports, simple bugs).
  2. **mypy**: static type checker (catches type mismatches).
  3. **pytest coverage**: enforces minimum test coverage threshold.
- All checks run in CI before merge. Tests are async-aware for Celery and FastAPI.
- Why chosen: pytest is Python standard. Playwright for realistic UI testing. ruff/mypy are fast and maintainable for growing codebase.
- Implementation impact: conftest.py for fixtures, @pytest.mark.asyncio for async tests, CI matrix for Python versions.

---

### 11.2 Module Architecture and Code Organization

#### 11.2.1 Directory Structure
```
alpmark/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── connectors.py
│   │   │   │   ├── metrics.py
│   │   │   │   ├── recommendations.py
│   │   │   │   ├── alerts.py
│   │   │   │   ├── exports.py
│   │   │   │   └── audit.py
│   │   │   └── dependencies.py  # auth, tenant context
│   │   └── exceptions.py  # error handlers
│   ├── core/
│   │   ├── config.py  # settings, vault secrets
│   │   ├── security.py  # JWT validation, RBAC checks
│   │   └── logging.py  # structured logs, OpenTel middleware
│   ├── models/
│   │   ├── db.py  # SQLAlchemy ORM models
│   │   ├── schemas.py  # Pydantic request/response models
│   │   └── enums.py  # status values, constants
│   ├── services/
│   │   ├── connector.py  # connector sync orchestration
│   │   ├── recommendation.py  # rule engine
│   │   ├── alert.py  # threshold + anomaly detection
│   │   ├── export.py  # data export logic
│   │   └── audit.py  # audit event recording
│   ├── connectors/
│   │   ├── base.py  # abstract connector interface
│   │   ├── shopify.py  # Shopify adapter
│   │   ├── meta.py  # Meta Ads adapter
│   │   └── google_ads.py  # Google Ads adapter
│   ├── rules/
│   │   ├── pack_v1.py  # rule definitions (e.g., margin, churn)
│   │   └── evaluator.py  # rule execution engine
│   ├── workers/
│   │   ├── sync.py  # Celery task: connector sync
│   │   ├── recommendation.py  # Celery task: generation
│   │   ├── alert.py  # Celery task: detection
│   │   └── export.py  # Celery task: export + share
│   └── db/
│       ├── session.py  # SQLAlchemy session factory
│       ├── repository.py  # base class for data access
│       └── migrations/  # Alembic migration files
├── tests/
│   ├── unit/
│   │   ├── test_rules.py
│   │   ├── test_services.py
│   │   └── test_security.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   ├── test_tenant_isolation.py
│   │   └── test_connectors.py
│   └── e2e/
│       └── test_recommendation_flow.py  # Playwright
├── frontend/  # Next.js app
│   ├── pages/
│   ├── components/
│   ├── lib/
│   └── public/
├── docker/
│   ├── Dockerfile.app
│   └── Dockerfile.worker
├── infra/
│   ├── main.tf  # Terraform for AWS resources
│   └── docker-compose.yml  # local dev
├── scripts/
│   ├── backfill_orders.py
│   ├── seed_roles.py
│   └── healthcheck.sh
├── main.py  # FastAPI app entry
├── celery_app.py  # Celery configuration
├── requirements.txt  # Python dependencies
└── README.md
```

#### 11.2.2 Key Modules and Responsibilities

1. **app/api/v1/endpoints/**
   - Each module (connectors, metrics, etc.) handles HTTP routing for that domain.
   - Dependency injection for auth, tenant context, DB session.
   - Request validation via Pydantic schemas.

2. **app/services/**
   - Business logic layer. Called by API endpoints and workers.
   - Each service method is transactional and testable in isolation.
   - Example: `recommendation_service.generate_for_tenant(tenant_id)` returns list of recommendations.

3. **app/connectors/**
   - Abstract base class defines interface (fetch, normalize, error handling).
   - Concrete adapters (Shopify, Meta, Google) implement source-specific logic.
   - Retry and backoff built in.

4. **app/rules/**
   - `pack_v1.py` defines rule objects (conditions, actions, thresholds).
   - `evaluator.py` takes a rule pack version and tenant data, returns matched recommendations.
   - Versioning allows safe rollout of new rules.

5. **app/workers/**
   - Celery tasks for async jobs (sync, recommendations, alerts, exports).
   - Idempotent: safe to retry if job fails.
   - Include retry logic, error logging, and result callbacks.

6. **app/db/**
   - `session.py` manages SQLAlchemy engine and session pooling.
   - `repository.py` is base class for data access; enforces tenant_id filters.
   - Example: `OrderRepository.get_by_tenant_and_date(tenant_id, date_start, date_end)`.

---

### 11.3 API Endpoints (Key Examples)

All endpoints require JWT token in `Authorization: Bearer <token>`.

#### Connector Management
```
POST /api/v1/connectors
  body: { type: "shopify", auth_mode: "oauth" }
  response: { id, auth_url } → user visits auth_url

POST /api/v1/connectors/{id}/sync
  response: { job_id } → async, track via GET /jobs/{job_id}

GET /api/v1/connectors/{id}/freshness
  response: { freshness_bucket, last_sync_at, status }
```

#### Recommendations
```
GET /api/v1/recommendations?status=New&confidence_min=0.7
  response: [{ id, title, rationale, evidence: [{metric, value}] }]

POST /api/v1/recommendations/{id}/review
  body: { decision: "Approved", reason: "..." }
  response: { status: "Approved", approval_record_id }

POST /api/v1/recommendations/{id}/simulate
  body: { scenario: { sku_price_change: 0.15 } }
  response: { simulation_id, output: {...} }
```

#### Alerts
```
GET /api/v1/alerts?type=threshold&status=Active
  response: [{ id, title, detected_at, suppressed: bool }]

POST /api/v1/alerts/{id}/ack
  body: { note: "..." }
  response: { status: "Acknowledged" }
```

#### Exports and Sharing
```
POST /api/v1/exports
  body: { type: "metrics", filters: { metric_keys: [...] } }
  response: { export_id, status: "processing" }

POST /api/v1/exports/{id}/share
  body: { recipient_emails: ["alice@acme.com"] }
  response: { share_id, share_url, expires_at }

GET /api/v1/shared/{share_id}/download
  (no tenant context; validates share_id and permissions)
  response: CSV or JSON file
```

---

### 11.4 Data Consistency and Transactions

1. **ACID guarantees via PostgreSQL**
   - Recommendation generation is atomic: all evidence, rationale, and status written in one transaction.
   - Approval workflow transitions validated by stored procedure or app logic before commit.

2. **Idempotent Jobs**
   - Sync jobs are keyed by (connector_id, sync_window). Rerunning same job is safe.
   - Recommendation jobs use versioned rule pack; re-running produces same output.
   - Alert jobs use timestamp-based windows to avoid duplicates.

3. **Tenant Isolation Enforcement**
   - Every SELECT/INSERT/UPDATE/DELETE filtered by tenant_id at the query level.
   - No query should ever omit tenant_id filter.
   - Integration tests verify this (e.g., "User from Tenant A cannot see Tenant B's orders").

---

### 11.5 Security Implementation

1. **Secret Management**
   - Connector OAuth tokens and API keys stored in AWS Secrets Manager (vault).
   - Application code never logs or prints secrets.
   - Credentials retrieved at sync time, used in-memory, discarded after request.

2. **RBAC Enforcement**
   - Role enum: admin, operator, analyst, finance.
   - Permission matrix: operator can generate recommendations but not delete audit logs.
   - Enforced via decorator: `@require_permission("view_metrics")` on endpoint.

3. **Audit Logging**
   - Every mutation (create/update/delete, approval, alert acknowledgment) logged to audit_event table.
   - Immutable: no deletes of audit records.
   - Includes actor (user email), timestamp, before/after state, trace_id for correlation.

4. **Rate Limiting**
   - Per-user limit: 100 API requests/minute.
   - Per-tenant limit: 1000 requests/minute.
   - Redis stores counter; FastAPI middleware enforces.

---

### 11.6 Development Workflow

1. **Branch and PR**
   - Feature branches: `feature/FR-052-order-history`
   - Each PR must pass CI: ruff + mypy + pytest + coverage threshold.
   - Code review required before merge to main.

2. **Local Development**
   - `docker-compose up` starts PostgreSQL, Redis, app, worker.
   - `pytest` runs all tests locally with same DB/Redis as production.
   - `alembic upgrade head` applies pending migrations.

3. **Deployment**
   - Push to main → GitHub Actions triggers build.
   - Tests run; if pass, Docker image pushed to ECR.
   - Terraform applies infra changes.
   - ECS task definition updated and new containers deployed.
   - Canary health checks ensure service is up before routing traffic.

---

### 11.7 Rollback and Rollforward Strategy

1. **Application Rollback**
   - Tag each Docker image with git commit SHA.
   - ECS task definition rollback: point to previous image tag.
   - Feature flags allow runtime disable of new features without re-deploy.

2. **Database Migration Rollback**
   - Every migration in Alembic must have `upgrade()` and `downgrade()`.
   - Downgrade rolls back schema to previous version.
   - Data recovery from backups if data was lost.

3. **Data Backups**
   - RDS automated snapshots daily.
   - Ability to restore to point-in-time within 7 days.
   - Test restore monthly.

---

### 11.8 Testing Strategy Mapped to FRs

| FR | Feature | Test Type | Framework | Example |
|---|---|---|---|---|
| FR-001 to FR-006 | Connector sync | Integration | pytest + httpx | `test_shopify_sync_completes_within_ttl()` |
| FR-010 to FR-020 | Metrics computation | Unit | pytest | `test_margin_calc_with_discount()` |
| FR-030 to FR-040 | Recommendations | Unit + Integration | pytest | `test_overstock_rule_fires_when_qty_gt_60d()` |
| FR-050 to FR-060 | Alerts | Integration | pytest | `test_margin_alert_emitted_within_1hr_sla()` |
| FR-070 to FR-080 | Exports and sharing | Integration | pytest + httpx | `test_export_shared_link_valid_24h()` |
| FR-090 to FR-100 | Approvals and workflow | Unit | pytest | `test_recommendation_state_transition_valid()` |
| Full user flow | Recommendation to approval to outcome | E2E | Playwright | `test_user_generates_views_approves_tracks_outcome()` |

---

### 11.9 Monitoring and Alerting (SLOs)

| Metric | SLO Target | Monitored By | Alert Threshold |
|---|---|---|---|
| API p95 latency | < 500ms | Prometheus + Grafana | p95 > 1000ms → page on-call |
| Sync success rate | 95% per connector | Prometheus | < 90% for 15 min → Slack alert |
| Recommendation generation time | < 5s | OpenTel traces | > 10s → investigate |
| Alert emission SLA | 95% within 1 hour | Audit events + Prometheus | > 10% miss → page on-call |
| Database connection pool exhaustion | < 5% events/week | RDS metrics | any spike → investigate |
| Sentry error rate | < 10 errors/day on main | Sentry dashboard | > 50/day → Slack alert |

---

### 11.10 Deployment Environments

1. **Development (local)**
   - docker-compose stack.
   - Seed data for testing.
   - Hot reload enabled.

2. **Staging (AWS)**
   - Same architecture as production.
   - Snapshot of production data (anonymized).
   - Used for QA, load testing, final sign-off before production deploy.

3. **Production (AWS)**
   - High-availability setup (multi-AZ).
   - Blue-green deployments to minimize downtime.
   - Audit logging and monitoring enabled.
   - Backup and disaster recovery tested weekly.

---

### 11.11 Step 11 Summary

This technical specification locks the engineering choices for AlpMark:
- **Backend**: Python + FastAPI + SQLAlchemy for maintainable, testable analytics logic.
- **Jobs**: Celery + Redis for reliable async connector sync and alert pipelines.
- **Data**: PostgreSQL with strict tenant_id enforcement and relational integrity.
- **Frontend**: Next.js + TypeScript for responsive UX and auth integration.
- **Security**: OAuth2 (managed) + RBAC + audit logging + vault-backed secrets.
- **Infrastructure**: Containerized on AWS Fargate + RDS + ElastiCache for low ops overhead.
- **Quality**: pytest + ruff + mypy in CI; comprehensive unit/integration/e2e coverage.

Implementation is now ready to move to Step 12 (Phase Plan) after your approval.
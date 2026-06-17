# AlpMark - Notion Workspace Sync
_Last synced: 2026-06-02 11:43:01_

---

## 00- The Overview

### Untitled

_⚠ No access — share this database with the AlpMark VSCode MCP integration in Notion._

### Untitled

_⚠ No access — share this database with the AlpMark VSCode MCP integration in Notion._

### Untitled

_⚠ No access — share this database with the AlpMark VSCode MCP integration in Notion._

### Untitled

_⚠ No access — share this database with the AlpMark VSCode MCP integration in Notion._

### Untitled

_⚠ No access — share this database with the AlpMark VSCode MCP integration in Notion._

### Untitled

_⚠ No access — share this database with the AlpMark VSCode MCP integration in Notion._

### Untitled

_⚠ No access — share this database with the AlpMark VSCode MCP integration in Notion._

### Untitled

_⚠ No access — share this database with the AlpMark VSCode MCP integration in Notion._

## 01-Phases

| Start Date | Entry Criteria | Status | Phase Name | Objective | End Date | Exit Criteria | Phase ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-08-10 | PH-05 marked Complete. Staging release candidate available. | Not started | Pilot Launch Readiness | Final verification, UAT, observability checks, launch gate validation, and go/no-go. | 2026-08-14 | MS-13 complete. All required launch gates passed. Go/No-Go decision recorded as Go. | PH-06 |
| 2026-08-03 | PH-04 marked Complete. Core product workflows stable in staging. | Not started | Support Tooling and Hardening | Build support diagnostics, controlled support access, DR/privacy controls, and operational hardening. | 2026-08-07 | MS-12 complete. Support tooling (FR-092 to FR-106) complete. Backup/restore validated. Privacy workflows validated. | PH-05 |
| 2026-07-13 | PH-03 marked Complete. Recommendation APIs stable. | Not started | Workflow, Alerts, Simulation, UI | Build approvals, alerts/notifications, simulation, exports/sharing, and main frontend views. | 2026-07-31 | MS-09, MS-10, MS-11 complete. Alert pipeline live. Simulation works. Export/share works with permissions. Core UI flows complete. | PH-04 |
| 2026-06-22 | PH-02 marked Complete. Normalized data flowing daily with acceptable freshness. | Not started | Metrics and Recommendation Engine | Build metric computation, deterministic rules, recommendation lifecycle, and evidence generation. | 2026-07-10 | MS-06, MS-07, MS-08 complete. KPI engine working. Rule pack v1 running. Recommendation lifecycle + outcome tracking functional. | PH-03 |
| 2026-06-01 | PH-01 marked Complete. DB schema stable. Secrets manager configured. | Not started | Connector and Data Layer | Build connectors, sync scheduler, normalization pipeline, and freshness logic. | 2026-06-19 | MS-03, MS-04, MS-05 complete. Shopify/Meta/Google sync working. Scheduled sync + retry/backoff active. Freshness indicators visible. | PH-02 |
| 2026-05-18 | Step 11 approved and locked. Final stack locked (Python/FastAPI/Next/Postgres/Redis/AWS). Workspace/repo access available. | In progress | Foundation Setup | Set up repo, infra, auth foundation, core schema, CI/CD, and Notion workspace. | 2026-05-29 | MS-01 and MS-02 complete. CI pipeline passing. Auth + RBAC working. Base schema + migrations applied. Notion structure created. | PH-01 |

## 02-Milestones

| Status | Exit Criteria | Linked NFRs | Linked FRs | Phase | Description | Entry Criteria | Milestone Name | Due Date | Milestone ID |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Not started | E2E passes, load and SLA checks pass, security checks pass, launch gates reviewed, formal Go/No-Go decision logged. | NFR-001 to NFR-024 verification | Verifies FR-001 to FR-125 readiness | 1 linked | Execute full verification, UAT, launch gate checks, and formal launch decision process. | PH-06 In Progress. MS-12 complete. | Final Verification and Go/No-Go | 2026-08-14 | MS-13 |
| Not started | Support ticket lifecycle works, scoped/time-bound support access enforced, closure requirements enforced, DR backup/restore validated, privacy workflows verified. | NFR-015, NFR-016, NFR-018, NFR-024 | FR-092 to FR-106 | 1 linked | Build support queue, diagnostics, scoped support access, closure controls, and hardening for DR/privacy requirements. | PH-05 In Progress. MS-11 complete. | Support Tooling and Operational Hardening | 2026-08-07 | MS-12 |
| Not started | Core persona flows usable end-to-end, accessibility baseline met, browser compatibility validated, localization/currency display correct, dashboard performance target met. | NFR-008, NFR-019, NFR-020, NFR-021, NFR-022 | FR-018, FR-022, FR-025, FR-030, FR-031, FR-040, FR-047, FR-049, FR-055, FR-058 | 1 linked | Complete Next.js UI for persona workflows including dashboards, recommendations, simulation, alerts, and exports. | MS-10 complete APIs available. | Frontend Completion for All Core Flows | 2026-07-31 | MS-11 |
| Not started | Baseline/upside/downside scenarios available, simulations saved/reopened, exports generated and shareable with permission enforcement and delivery logs. | NFR-010, NFR-016 | FR-008, FR-034, FR-046, FR-055, FR-057, FR-070, FR-080, FR-081 to FR-091 | 1 linked | Build simulation workspace and scoped export/share flows with permission checks and email delivery. | MS-09 complete. | Simulation and Export/Share | 2026-07-24 | MS-10 |
| Not started | Alert types fire correctly, routing/escalation works, in-app + email delivery works, stale/confidence flags included, alert history immutable and auditable. | NFR-009, NFR-023 | FR-067, FR-107 to FR-115, FR-117 to FR-125 | 1 linked | Build threshold/anomaly detection, routing, escalation, confidence labeling, notification center, and immutable alert history. | PH-04 In Progress. MS-08 complete. | Alerts and Notification Infrastructure | 2026-07-17 | MS-09 |
| Not started | Full lifecycle transitions work, suppression rules apply correctly, delegation works, implementation gap flags appear, outcomes can be observed and compared. | NFR-005, NFR-012 | FR-022 to FR-024, FR-032, FR-033, FR-037, FR-040, FR-042 to FR-045, FR-051, FR-056, FR-063, FR-068, FR-069, FR-072 to FR-078 | 1 linked | Build lifecycle states, review/approve/reject, suppression logic, delegation, implementation gap detection, outcome observation. | MS-07 complete. | Recommendation Lifecycle and Decision Tracking | 2026-07-10 | MS-08 |
| Not started | Rule engine executes deterministically, recommendation triggers match defined conditions, confidence and rationale are produced consistently. | NFR-014 | FR-021, FR-071, FR-079 | 1 linked | Implement rule engine and first rule pack for key recommendation domains with explainable outputs. | MS-06 complete. | Deterministic Recommendation Rule Pack v1 | 2026-07-03 | MS-07 |
| Not started | All core metric calculations return expected results, cost input history/versioning works, tenant currency formatting/logic applied in calculations. | NFR-013, NFR-022 | FR-018 to FR-020, FR-026 to FR-029, FR-035, FR-036, FR-038, FR-039, FR-041, FR-048, FR-050, FR-052 to FR-054, FR-058 to FR-066 | 1 linked | Build KPI, margin, cohort, churn, inventory, and cost-driver computations including versioned cost inputs. | PH-03 In Progress. MS-05 complete with stable data flow. | Metrics and Financial/Inventory Computation | 2026-06-26 | MS-06 |
| Not started | Scheduler running, normalized tables populated, freshness labels visible, stale warnings enforced, retry policy active with terminal failure visibility. | NFR-006, NFR-007, NFR-012 | FR-014, FR-017, FR-024, FR-079, FR-120 | 1 linked | Implement scheduled jobs, normalized data models, freshness labels, stale-data handling, retry/backoff. | MS-04 complete. | Scheduler, Normalization, Freshness | 2026-06-19 | MS-05 |
| Not started | Both connectors connect/reconnect successfully, scheduled and manual sync operate, token expiry reminders wired, sync failure alerts triggered. | NFR-002, NFR-007 | FR-009 to FR-013, FR-015, FR-016, FR-115, FR-116 | 1 linked | Build Meta and Google Ads OAuth connectors with synced spend/campaign data and recovery flows. | MS-03 complete. | Meta and Google Ads Connectors | 2026-06-12 | MS-04 |
| Not started | Shopify connect/reconnect works, data sync runs, manual re-sync works, status and last sync time visible, failures logged clearly. | NFR-002, NFR-007 | FR-009 to FR-013, FR-015, FR-016 | 1 linked | Build Shopify OAuth, token handling, sync and manual re-sync with status visibility. | PH-02 In Progress. MS-02 complete. | Shopify Connector End-to-End | 2026-06-05 | MS-03 |
| Not started | Tenant create flow works, user invite/role flow works, onboarding checklist visible and updating, RBAC enforced on core endpoints, audit events stored immutably. | NFR-001, NFR-002, NFR-004, NFR-005, NFR-016 | FR-001 to FR-008 | 1 linked | Implement tenant model, user lifecycle basics, onboarding checklist, auth integration, role model, immutable audit foundation. | MS-01 complete. DB and secrets access available | Auth, RBAC, Tenant Core, Audit Base | 2026-05-29 | MS-02 |
| In progress | Repo created, branching rules set, CI pipeline running (lint, typecheck, tests), Docker build works locally and in CI. | NFR-003, NFR-017 | Foundation for all FRs | 1 linked | Set up codebase, Docker, CI/CD, cloud project, and local dev workflow. | PH-01 In Progress. Tech stack decisions locked. | Repo and Delivery Foundation | 2026-05-22 | MS-01 |

## 03-Tasks

| Task Name	 | Blocked By | PR/Commit Link | Priority | Notes | Phase | Week | Milestone | Status | FR/NFR Reference | Task ID  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Build frontend app shell and tenant auth session | 0 | [commit](#) | P0 | App shell (Header, Sidebar, OnboardingPanel, AppShell wrapper) complete. Session management via JWT. Hydration errors resolved with dynamic imports. Dark/light theme toggle working. Responsive layout tested. All quality gates passing: typecheck 0 errors, lint 0 errors, tests passing. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W8 | 1 linked | **Done** ✅ | FR-018 | T-088 |
| Build dashboard pages for executive growth retention finance operations | T-088 | | P0 | Build 5 persona-specific dashboard pages with KPI cards, trend indicators, data tables, and drill-down capabilities. Each dashboard displays real-time KPI metrics using KPI Card pattern (40–48px mono numbers, trend arrows, target comparisons). Include metric info popovers on every KPI. Baseline dashboard layout: 4-column KPI grid (top), data section (middle), alerts/insights section (bottom). All dashboards responsive (mobile/tablet/desktop). Dark mode fully supported with contrast validation. Milestone/Phase reference: MS-11 / PH-04. Effort: 1.0 | 1 items | W9 | 1 linked | **In Progress** 🔄 | FR-018, FR-025, FR-040, FR-047, FR-058 | T-089 |
| Build LLM narration layer for recommendations | 0 linked |  | P1 | Takes simulation output (x*, evidence chain, projected impact table, confidence level, data freshness) and generates recommendation narrative card. LLM generates words and urgency framing only — never generates numbers. All numerical values come exclusively from simulation output. Generates: why-now urgency context, plain-language action description, risk framing for downside scenario. Every number shown in the narrative must include a source citation traceable to simulation payload. Milestone/Phase reference: MS-10 / PH-04. Effort: 1.0 | 1 items | W10 | 1 linked | Backlog | FR-071, FR-079 | T-119 |
| Build response function model fitting per simulation domain | 0 linked |  | P0 | Fits smooth response curves from the brand's historical snapshot data for each simulation domain: acquisition (ROAS vs spend), margin (contribution margin vs cost input), retention (repeat rate vs CRM lever), inventory (stockout risk vs reorder point), ops (fulfillment cost vs order volume), executive (blended margin vs mix). Uses regression/polynomial curve fitting to produce a smooth model of how a KPI responds to changes in the control variable. Required as input to T-081 scipy.optimize optimizer — optimizer needs a differentiable function, not raw noisy snapshot data. 90-day minimum data gate enforced as hard prerequisite before any response function is fitted. Milestone/Phase reference: MS-07 / PH-03. Effort: 1.0 | 1 items | W7 | 1 linked | Backlog | FR-071, NFR-014 | T-118 |
| Build recommendation-to-simulation launch with pre-populated parameters | 2 linked |  | P1 | Simulate action present on all recommendation views | 1 items | W10 | 1 linked | Backlog |  FR-126 | T-117 |
| Conduct final go or no go decision | 0 linked |  | P0 | Launch decision logged with evidence. Milestone/Phase reference: MS-13 / PH-06. Effort: 0.5 | 1 items | W13 | 1 linked | Backlog | Launch governance | T-116 |
| Run launch gate checklist review | 1 linked |  | P0 | All required launch gates reviewed. Milestone/Phase reference: MS-13 / PH-06. Effort: 0.5 | 1 items | W13 | 1 linked | Backlog | LG-01 to LG-12 | T-115 |
| Validate observability dashboards and paging | 1 linked |  | P1 | Metrics traces errors and alerts active. Milestone/Phase reference: MS-13 / PH-06. Effort: 0.5 | 1 items | W13 | 1 linked | Backlog | NFR-017, NFR-023 | T-114 |
| Run end to end user journey suite | 2 linked |  | P0 | Core persona journeys pass. Milestone/Phase reference: MS-13 / PH-06. Effort: 0.5 | 1 items | W13 | 1 linked | Backlog | NFR-019 | T-111 |
| Run load and SLA validation tests | 1 linked |  | P0 | Performance and alert SLA targets validated. Milestone/Phase reference: MS-13 / PH-06. Effort: 0.5 | 1 items | W13 | 1 linked | Backlog | NFR-008, NFR-009, NFR-011 | T-112 |
| Run security and tenant isolation audit | 1 linked |  | P0 | No critical security and isolation gaps. Milestone/Phase reference: MS-13 / PH-06. Effort: 0.5 | 1 items | W13 | 1 linked | Backlog | NFR-001, NFR-002, NFR-004, NFR-005 | T-113 |
| Build support escalation flow | 1 linked |  | P1 | Escalation logged with severity and impact. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | FR-103 | T-105 |
| Build support audit and sensitive field masking | 1 linked |  | P0 | Masking and full support audit trail enforced. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | FR-104, FR-105, FR-106 | T-106 |
| Run full backend integration regression | 5 linked |  | P0 | Critical integrations pass in staging. Milestone/Phase reference: MS-13 / PH-06. Effort: 0.5 | 1 items | W13 | 1 linked | Backlog | FR-001 to FR-125 | T-110 |
| Baseline support MTTR metrics and reporting | 1 linked |  | P2 | MTTR metrics visible for support workflows. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | NFR-018 | T-109 |
| Build support notes and mandatory closure metadata | 2 linked |  | P1 | Resolution fields mandatory for closure. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | FR-099, FR-100, FR-101 | T-104 |
| Build time bound access expiry and closure revoke | 1 linked |  | P0 | Temporary access auto revoked by policy. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | FR-098, FR-102, NFR-024 | T-103 |
| Build support manual resync action | 1 linked |  | P1 | Support can trigger source resync. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | FR-096 | T-102 |
| Build support diagnostic view APIs | 4 linked |  | P0 | Sync token alert recommendation diagnostics shown. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | FR-095 | T-101 |
| Execute backup and restore drill | 1 linked |  | P0 | RPO and RTO validated in test run. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | NFR-015 | T-107 |
| Tune dashboard performance to p95 target | 1 linked |  | P0 | Core dashboard p95 target achieved. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W11 | 1 linked | Backlog | NFR-008 | T-098 |
| Build scoped support access request flow | 2 linked |  | P0 | Scoped access request and approval supported. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | FR-094, FR-097 | T-100 |
| Execute privacy workflow validation | 2 linked |  | P1 | Privacy export delete paths verified. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | NFR-016 | T-108 |
| Implement UI localization and currency formatting | 1 linked |  | P1 | Tenant locale and currency formatting applied. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W11 | 1 linked | Backlog | NFR-022 | T-095 |
| Run cross browser validation suite | 1 linked |  | P1 | Chrome Safari Edge support validated. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W11 | 1 linked | Backlog | NFR-021 | T-097 |
| Build export share UI with status tracking | 1 linked |  | P1 | Export status and share actions complete. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W11 | 1 linked | Backlog | FR-034, FR-046, FR-057, FR-070, FR-080, FR-091 | T-093 |
| Build annotation and saved view UI | 1 linked |  | P2 | Save views and annotation UI complete. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W11 | 1 linked | Backlog | FR-032, FR-033, FR-045, FR-068 | T-094 |
| Run accessibility remediation for core flows | 1 linked |  | P0 | No critical WCAG failures in core flows. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W11 | 1 linked | Backlog | NFR-020 | T-096 |
| Build alert center and notification UI | 1 linked |  | P1 | Filter acknowledge dismiss flows available. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W11 | 1 linked | Backlog | FR-123 | T-091 |
| Build recommendation review and lifecycle UI | 1 linked |  | P0 | Review approve reject implemented in UI. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W11 | 1 linked | Backlog | FR-072, FR-073, FR-078 | T-090 |
| Build signed file links and expiry management | 0 linked |  | P1 | Signed links expire correctly. Milestone/Phase reference: MS-10 / PH-04. Effort: 0.5 | 1 items | W10 | 1 linked | Backlog | FR-091 | T-087 |
| Build scoped export sharing with permission checks | 0 linked |  | P0 | Sharing respects recipient permissions. Milestone/Phase reference: MS-10 / PH-04. Effort: 0.5 | 1 items | W10 | 1 linked | Backlog | FR-008 | T-086 |
| Build simulation workspace UI | 1 linked |  | P1 | Simulation create run compare works. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W11 | 1 linked | Backlog | FR-081 to FR-090 | T-092 |
| Build dashboard pages for executive growth retention finance operations | 10 linked |  | P0 | Core dashboards render live data. Milestone/Phase reference: MS-11 / PH-04. Effort: 1.0 | 1 items | W11 | 1 linked | Backlog | FR-018, FR-025, FR-040, FR-047, FR-058 | T-089 |
| Build simulation side by side compare and confidence warnings | 2 linked |  | P1 | Delta compare and quality warnings shown. Milestone/Phase reference: MS-10 / PH-04. Effort: 0.5 | 1 items | W10 | 1 linked | Backlog | FR-088, FR-089 | T-083 |
| Build growth retention finance operations executive simulation inputs | 3 linked |  | P0 | All simulation domains supported. Milestone/Phase reference: MS-10 / PH-04. Effort: 1.0 | 1 items | W10 | 1 linked | Backlog | FR-082, FR-083, FR-084, FR-085, FR-086 | T-082 |
| Build save and revisit simulation scenarios | 2 linked |  | P1 | Scenario persistence and reload supported. Milestone/Phase reference: MS-10 / PH-04. Effort: 0.5 | 1 items | W10 | 1 linked | Backlog | FR-090 | T-084 |
| Build export generation service for all domains | 1 linked |  | P0 | Exports generated in PDF and CSV. Milestone/Phase reference: MS-10 / PH-04. Effort: 0.5 | 1 items | W10 | 1 linked | Backlog | FR-034, FR-046, FR-057, FR-070, FR-080, FR-091 | T-085 |
| Build escalation and acknowledgement flows | 3 linked |  | P1 | Escalation and ack states persisted. Milestone/Phase reference: MS-09 / PH-04. Effort: 0.5 | 1 items | W9 | 1 linked | Backlog | FR-122, FR-123 | T-078 |
| Build immutable alert history log | 1 linked |  | P1 | Alert history auditable and immutable. Milestone/Phase reference: MS-09 / PH-04. Effort: 0.5 | 1 items | W9 | 1 linked | Backlog | FR-125 | T-080 |
| Build early warning and operational anomaly alerts | 1 linked |  | P1 | Warnings and anomaly alerts generated correctly. Milestone/Phase reference: MS-09 / PH-04. Effort: 0.5 | 1 items | W9 | 1 linked | Backlog | FR-118, FR-119, FR-067 | T-076 |
| Build stale data and confidence injection in alert payloads | 1 linked |  | P1 | Alert payload includes confidence and stale flag. Milestone/Phase reference: MS-09 / PH-04. Effort: 0.5 | 1 items | W9 | 1 linked | Backlog | FR-120, FR-121 | T-077 |
| Build email notification delivery and retries | 1 linked |  | P1 | Retry policy and failure logging active. Milestone/Phase reference: MS-09 / PH-04. Effort: 0.5 | 1 items | W9 | 1 linked | Backlog | FR-124, NFR-023 | T-079 |
| Build frontend app shell and tenant auth session | 2 linked |  | P0 | Session based tenant aware app shell ready. Milestone/Phase reference: MS-11 / PH-04. Effort: 0.5 | 1 items | W11 | 1 linked | Backlog | FR-018 | T-088 |
| Build domain alert handlers for KPI stock churn sync margin | 4 linked |  | P0 | Domain handlers return full payloads. Milestone/Phase reference: MS-09 / PH-04. Effort: 1.0 | 1 items | W9 | 1 linked | Done | FR-112, FR-113, FR-114, FR-115, FR-117 | T-075 |
| Build support ticket queue APIs | 4 linked |  | P0 | Ticket create assign update complete. Milestone/Phase reference: MS-12 / PH-05. Effort: 0.5 | 1 items | W12 | 1 linked | Backlog | FR-092, FR-093 | T-099 |
| Build simulation core with baseline upside downside | 3 linked |  | P0 | Three scenario model always available. Milestone/Phase reference: MS-10 / PH-04. Effort: 1.0 This task covers background auto-simulation only — runs after rule engine fires, uses fitted response functions from T-118, runs scipy.optimize to find x* (true mathematical optimum), attaches x* and evidence to recommendation. User never triggers this path directly. User-interactive simulation workspace (what-if exploration) is covered by T-082 and T-117. Same underlying optimizer evaluates any user-specified input in the interactive workspace. | 1 items | W10 | 1 linked | Backlog | FR-081, FR-087 | T-081 |
| Build threshold alert generation pipeline | 2 linked |  | P0 | Threshold alerts generated within SLA. Milestone/Phase reference: MS-09 / PH-04. Effort: 0.5 | 1 items | W9 | 1 linked | Done | FR-110 | T-074 |
| Build anomaly detection service | 1 linked |  | P0 | Baseline and dispersion based anomaly detection active. Milestone/Phase reference: MS-09 / PH-04. Effort: 0.5 | 1 items | W9 | 1 linked | Done | FR-109, FR-111 | T-073 |
| Build alert configuration APIs | 2 linked |  | P0 | Thresholds routing and recipients configurable. Milestone/Phase reference: MS-09 / PH-04. Effort: 0.5 | 1 items | W9 | 1 linked | Done | FR-107, FR-108 | T-072 |
| Build retention read only acquisition context API | 1 linked |  | P2 | Retention users can view acquisition context only. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-043 | T-070 |
| Build custom segment definition APIs | 1 linked |  | P1 | Segment create update reuse works. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-044 | T-071 |
| Build finance high impact cost change confirmation gate | 1 linked |  | P1 | Confirmation required before propagation. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-051 | T-067 |
| Build warehouse level inventory views | 1 linked |  | P1 | Per location and fallback aggregate supported. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-063 | T-069 |
| Build annotation service for analyses and cohorts | 1 linked |  | P1 | Timestamped annotations stored. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-033, FR-045, FR-068 | T-065 |
| Build side by side cohort comparison service | 1 linked |  | P1 | Cohorts compared with overlay metrics. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-037 | T-066 |
| Build historical restatement engine | 1 linked |  | P1 | Historical period restatement supported. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-056 | T-068 |
| Build saved analysis views and share metadata | 1 linked |  | P1 | Custom views can be saved and reused. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-032, FR-034 | T-064 |
| Build outcome observation and comparison pipeline | 1 linked |  | P0 | Before after impact and summary generated. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-069, FR-077, FR-078 | T-063 |
| Build implementation gap detection | 2 linked |  | P1 | Not implemented flags trigger on threshold. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-076 | T-062 |
| Build recommendation lifecycle state machine | 4 linked |  | P0 | Legal transitions only. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-072 | T-058 |
| Build delegation rules and revocation flow | 1 linked |  | P1 | Delegated approvals in policy scope. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-023, FR-075 | T-061 |
| Build suppression logic based on reject patterns | 1 linked |  | P0 | Suppression windows generated correctly. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-074 | T-060 |
| Build recommendation review endpoints | 3 linked |  | P0 | Approve reject with reasons enforced. Milestone/Phase reference: MS-08 / PH-03. Effort: 0.5 | 1 items | W8 | 1 linked | Ready | FR-073 | T-059 |
| Build recommendation evidence payload assembler | 1 linked |  | P1 | Evidence and rationale attached. Milestone/Phase reference: MS-07 / PH-03. Effort: 0.5 | 1 items | W7 | 1 linked | Done | FR-071 | T-057 |
| Build recommendation confidence model | 1 linked |  | P1 | Confidence reflects freshness completeness. Milestone/Phase reference: MS-07 / PH-03. Effort: 0.5 | 1 items | W7 | 1 linked | Done | FR-079, FR-121 | T-056 |
| Build rule pack v1 for major signal families | 5 linked |  | P0 | Rule coverage for priority domains complete. Milestone/Phase reference: MS-07 / PH-03. Effort: 1.0 Rules detect pattern/velocity/trajectory changes, not just threshold breaches. Example: ROAS declined 12% per week for 3 consecutive periods, not ROAS < 2.0. Change detection gate fires first — metric must have moved materially before simulation runs. Rule pack covers: acquisition (ROAS, CAC, payback), retention (churn velocity, cohort drop), margin (drift, cost spikes), inventory (stockout risk, overstock), and executive KPI signals. | 1 items | W7 | 1 linked | Done | FR-071 | T-054 |
| Build impact scoring for recommendation ranking | 1 linked |  | P1 | Impact x urgency ranking applied. Milestone/Phase reference: MS-07 / PH-03. Effort: 0.5 | 1 items | W7 | 1 linked | Done | FR-021 | T-055 |
| Build deterministic rule engine core | 3 linked |  | P0 | Same input same recommendation output. Milestone/Phase reference: MS-07 / PH-03. Effort: 1.0 Event-driven trigger on sync_complete. Three gates required before recommendation fires: (1) Change detection gate — metric moved materially in a meaningful direction. (2) Delta gate — x* (optimum) is meaningfully different from the brand's current state. (3) Impact floor gate — projected improvement exceeds minimum meaningful threshold scaled to brand revenue. Celery chain: sync_complete → trigger_rule_evaluation → create_recommendations. If all three gates pass, recommendation is created with evidence payload. If no signal detected, health summary only — no recommendation fires. | 1 items | W7 | 1 linked | Done | FR-071, NFR-014 | T-053 |
| Build currency and locale normalization in calculations | 1 linked |  | P1 | Tenant base currency applied consistently. Milestone/Phase reference: MS-06 / PH-03. Effort: 0.5 | 1 items | W6 | 1 linked | Done | NFR-022 | T-052 |
| Build operational impact computations | 1 linked |  | P1 | Lost revenue and logistics burden available. Milestone/Phase reference: MS-06 / PH-03. Effort: 0.5 | 1 items | W6 | 1 linked | Done | FR-064, FR-065, FR-066 | T-051 |
| Build full cost input version history | 2 linked |  | P0 | Full lineage from first value captured. Milestone/Phase reference: MS-06 / PH-03. Effort: 0.5 | 1 items | W6 | 1 linked | Done | FR-052, NFR-013 | T-049 |
| Build segment margin and return signal computations | 1 linked |  | P1 | Segment economics and retention signal ready. Milestone/Phase reference: MS-06 / PH-03. Effort: 0.5 | 1 items | W6 | 1 linked | Done | FR-041, FR-042 | T-046 |
| Build tiered cost input model and APIs | 2 linked |  | P1 | Tier and band input supported. Milestone/Phase reference: MS-06 / PH-03. Effort: 0.5 | 1 items | W6 | 1 linked | Done | FR-050 | T-048 |
| Build inventory risk computations | 3 linked |  | P0 | Low stock stockout overstock slow moving computed. Milestone/Phase reference: MS-06 / PH-03. Effort: 0.5 | 1 items | W6 | 1 linked | Done | FR-058, FR-059, FR-060, FR-061, FR-062 | T-050 |
| Build finance cost drivers and drift computations | 3 linked |  | P0 | Cost and drift calculations complete. Milestone/Phase reference: MS-06 / PH-03. Effort: 0.5 | 1 items | W6 | 1 linked | Done | FR-048, FR-049, FR-053, FR-054 | T-047 |
| Build retention and cohort metrics computation | 4 linked |  | P0 | Cohort curves and churn cadence ready. Milestone/Phase reference: MS-06 / PH-03. Effort: 0.5 | 1 items | W6 | 1 linked | Done | FR-035, FR-036, FR-038, FR-039, FR-040 | T-045 |
| Build acquisition metrics computation | 2 linked |  | P0 | ROAS CAC payback contribution computed. Milestone/Phase reference: MS-06 / PH-03. Effort: 0.5 | 1 items | W6 | 1 linked | Done | FR-026, FR-027, FR-028, FR-029 | T-044 |
| Implement stale data warning gate | 1 linked |  | P0 | Warning or hold logic enforced. Milestone/Phase reference: MS-05 / PH-02. Effort: 0.5 | 1 items | W5 | 1 linked | Done | FR-024, FR-079, FR-120 | T-040 |
| Add deterministic freshness label consistency tests | 1 linked |  | P1 | Same data gives same labels everywhere. Milestone/Phase reference: MS-05 / PH-02. Effort: 0.5 | 1 items | W5 | 1 linked | Done | NFR-012 | T-042 |
| Build executive KPI computation service | 7 linked |  | P0 | KPI and drift computed daily. Milestone/Phase reference: MS-06 / PH-03. Effort: 1.0 | 1 items | W6 | 1 linked | Done | FR-018, FR-019, FR-020 | T-043 |
| Add sync uptime and job metrics | 1 linked |  | P1 | Uptime and failure rate visible. Milestone/Phase reference: MS-05 / PH-02. Effort: 0.5 | 1 items | W5 | 1 linked | Done | NFR-006, NFR-017 | T-041 |
| Implement freshness label computation | 4 linked |  | P0 | High medium low freshness computed. Milestone/Phase reference: MS-05 / PH-02. Effort: 0.5 | 1 items | W5 | 1 linked | Done | FR-017 | T-039 |
| Implement sync retry and capped backoff | 1 linked |  | P0 | Retry policy enforced. Milestone/Phase reference: MS-05 / PH-02. Effort: 0.5 | 1 items | W5 | 1 linked | Done | NFR-007 | T-038 |
| Configure scheduled sync cadence by source | 4 linked |  | P0 | Celery beat schedules active. Milestone/Phase reference: MS-05 / PH-02. Effort: 0.5 | 1 items | W5 | 1 linked | Done | FR-014 | T-037 |
| Build actionable connector error mapping | 1 linked |  | P1 | User friendly errors returned. Milestone/Phase reference: MS-04 / PH-02. Effort: 0.5 | 1 items | W4 | 1 linked | Done | FR-016 | T-036 |
| Build connector failure alert creation | 2 linked |  | P1 | Failure alerts include source and reason. Milestone/Phase reference: MS-04 / PH-02. Effort: 0.5 | 1 items | W4 | 1 linked | Done | FR-115 | T-035 |
| Build Google spend sync task | 1 linked |  | P0 | Daily spend synced. Milestone/Phase reference: MS-04 / PH-02. Effort: 1.0 | 1 items | W4 | 1 linked | Done | FR-026, FR-027 | T-034 |
| Build Meta spend sync task | 3 linked |  | P0 | Daily spend synced. Milestone/Phase reference: MS-04 / PH-02. Effort: 1.0 | 1 items | W4 | 1 linked | Done | FR-026, FR-027 | T-033 |
| Build manual resync trigger endpoint | 1 linked |  | P1 | Resync creates queued job. Milestone/Phase reference: MS-03 / PH-02. Effort: 0.5 | 1 items | W3 | 1 linked | Done | FR-015 | T-029 |
| Build Google Ads OAuth connect flow | 2 linked |  | P0 | Google connection complete. Milestone/Phase reference: MS-04 / PH-02. Effort: 0.5 | 1 items | W4 | 1 linked | Done | FR-009 | T-032 |
| Build integration status API | 1 linked |  | P1 | Status, last sync, progress exposed. Milestone/Phase reference: MS-03 / PH-02. Effort: 0.5 | 1 items | W3 | 1 linked | Done | FR-016 | T-030 |
| Build Meta Ads OAuth connect flow | 2 linked |  | P0 | Meta connection complete. Milestone/Phase reference: MS-04 / PH-02. Effort: 0.5 | 1 items | W4 | 1 linked | Done | FR-009 | T-031 |
| Build Shopify inventory sync task | 2 linked |  | P1 | Inventory snapshots created. Milestone/Phase reference: MS-03 / PH-02. Effort: 0.5 | 1 items | W3 | 1 linked | Done | FR-058 | T-028 |
| Build connector reauthorize flow | 1 linked |  | P1 | Reauth rotates token successfully. Milestone/Phase reference: MS-03 / PH-02. Effort: 0.5 | 1 items | W3 | 1 linked | Done | FR-013 | T-026 |
| Build Shopify order sync task | 3 linked |  | P0 | Orders synced to normalized model. Milestone/Phase reference: MS-03 / PH-02. Effort: 1.0 | 1 items | W3 | 1 linked | Done | FR-014 | T-027 |
| Build token expiry monitoring job | 2 linked |  | P1 | 7 day and 1 day reminders generated. Milestone/Phase reference: MS-03 / PH-02. Effort: 0.5 | 1 items | W3 | 1 linked | Done | FR-012, FR-116 | T-025 |
| Store connector credentials in secrets vault | 4 linked |  | P0 | No plaintext credential storage. Milestone/Phase reference: MS-03 / PH-02. Effort: 0.5 | 1 items | W3 | 1 linked | Done | FR-011, NFR-002 | T-024 |
| Implement API key fallback for connector auth | 1 linked |  | P1 | Manual token flow supported. Milestone/Phase reference: MS-03 / PH-02. Effort: 0.5 | 1 items | W3 | 1 linked | Done | FR-010 | T-023 |
| Implement Shopify OAuth connect flow | 3 linked |  | P0 | OAuth connect and callback complete. Milestone/Phase reference: MS-03 / PH-02. Effort: 0.5 | 1 items | W3 | 1 linked | Done | FR-009 | T-022 |
| Implement governed privacy export and delete workflow | 2 linked |  | P1 | Privacy actions auditable. Milestone/Phase reference: MS-02 / PH-01. Effort: 0.5 | 1 items | W2 | 1 linked | Done | NFR-016 | T-021 |
| Implement tenant data access guards | 1 linked |  | P0 | tenant_id enforced in queries. Milestone/Phase reference: MS-02 / PH-01. Effort: 0.5 | 1 items | W2 | 1 linked | Done | NFR-001 | T-020 |
| Implement RBAC middleware | 3 linked |  | P0 | Unauthorized access blocked. Milestone/Phase reference: MS-02 / PH-01. Effort: 0.5 | 1 items | W2 | 1 linked | Done | NFR-004 | T-019 |
| Integrate managed auth provider | 6 linked |  | P0 | JWT auth integrated. Milestone/Phase reference: MS-02 / PH-01. Effort: 1.0 | 1 items | W2 | 1 linked | Done | NFR-004 | T-018 |
| Implement immutable audit event writer | 2 linked |  | P0 | Audit events append only. Milestone/Phase reference: MS-02 / PH-01. Effort: 0.5 | 1 items | W2 | 1 linked | Done | FR-008, NFR-005 | T-017 |
| Implement notification routing settings | 1 linked |  | P1 | Routing by alert type and channel. Milestone/Phase reference: MS-02 / PH-01. Effort: 0.5 | 1 items | W2 | 1 linked | Done | FR-007 | T-016 |
| Implement billing and seat management endpoints | 1 linked |  | P1 | Billing metadata operations supported. Milestone/Phase reference: MS-02 / PH-01. Effort: 0.5 | 1 items | W2 | 1 linked | Done | FR-006 | T-015 |
| Implement user role update and deactivation | 2 linked |  | P0 | Role changes and deactivate supported. Milestone/Phase reference: MS-02 / PH-01. Effort: 0.5 | 1 items | W2 | 1 linked | Done | FR-005 | T-014 |
| Implement invite user flow | 2 linked |  | P0 | Invite and activation token flow works. Milestone/Phase reference: MS-02 / PH-01. Effort: 0.5 | 1 items | W2 | 1 linked | Done | FR-004 | T-013 |
| Implement onboarding checklist | 1 linked |  | P1 | Checklist state is dynamic. Milestone/Phase reference: APIMS-02 / PH-01. Effort: 0.5 | 1 items | W2 | 1 linked | Done | FR-003 | T-012 |
| Implement account activation flow | 1 linked |  | P0 | Activation link flow works | 1 items | W2 | 1 linked | Done | FR-002 | T-011 |
| Implement tenant creation API | 4 linked |  | P0 | Tenant created with unique tenant ID | 1 items | W2 | 1 linked | Done | FR-001 | T-010 |
| Create base database schema and migrations | 6 linked |  | P0 | Core tables and migration chain ready | 1 items | W2 | 1 linked | Done | FR-001, FR-004 | T-009 |
| Configure local docker compose stack | 2 linked |  | P1 | App, worker, DB, Redis start locally | 1 items | W1 | 1 linked | Done | Platform foundation | T-008 |
| Provision base AWS resources | 1 linked |  | P0 | VPC, IAM, ECR, ECS base ready | 1 items | W1 | 1 linked | Done | NFR-003, NFR-017 | T-007 |
| Configure ruff, mypy, pytest baseline | 1 linked |  | P1 | Local and CI checks pass | 1 items | W1 | 1 linked | Done | Quality baseline | T-006 |
| Configure CI pipeline | 2 linked |  | P0 | Lint, typecheck, tests run on PR | 1 items | W1 | 1 linked | Done | NFR-017 | T-005 |
| Add Dockerfiles for app and worker | 2 linked |  | P0 | Images build successfully | 1 items | W1 | 1 linked | Done | Platform foundation | T-004 |
| Bootstrap Celery worker service | 1 linked |  | P0 | Worker boots and connects to Redis | 1 items | W1 | 1 linked | Done | Platform foundation | T-003 |
| Bootstrap FastAPI service | 3 linked |  | P0 | Health endpoint available | 1 items | W1 | 1 linked | Done | Platform foundation | T-002 |
| Create repository and base folder structure | 3 linked |  | P0 | Backend and frontend structure created | 1 items | W1 | 1 linked | Done | Platform foundation | T-001 |

## 04-Risks

| Risk Description | Status | Mitigation Plan | Impact | Phase | Likelihood | Risk ID  |
| --- | --- | --- | --- | --- | --- | --- |
| Pilot success criteria are unclear, making launch decision subjective. | Open | Define measurable launch gates upfront (SLA, E2E pass, UAT threshold, security checks) and require Go/No-Go decision template completion. | High | 1 linked | Medium | R-09 |
| Scope creep introduces extra features and delays delivery. | Open | Freeze scope to approved FR/NFR set, route all new ideas to backlog, and accept only critical changes via explicit weekly decision log. | High | 1 linked | High | R-08 |
| Managed auth free tier limits are exceeded earlier than expected. | Open | Track MAU/usage monthly, configure usage alerts, and maintain fallback migration plan to alternate provider if threshold nears. | Medium | 1 linked | Low | R-07 |
| AWS usage during test cycles exceeds expected budget. | Open | Use right-sized instances, enable budget alarms, auto-stop non-prod resources nightly, and review weekly cost dashboard. | Medium | 1 linked | Medium | R-06 |
| Tenant data leakage due to missing tenant filters or RBAC flaws. | Open | Enforce tenant_id at repository layer, mandatory auth/RBAC middleware, automated tenant boundary tests in CI, and audit access events. | Critical | 1 linked | Low | R-05 |
| Recommendation false positives reduce user trust and adoption. | Open | Use deterministic explainable rules, show rationale/evidence, add suppression logic for repeated declines, and run review calibration weekly. | High | 1 linked | Medium | R-04 |
| Source outages or connector issues cause stale data and poor recommendation quality. | Open | Enforce freshness indicators and stale-data gating, surface confidence reduction, and trigger sync failure alerts with clear remediation steps. | High | 1 linked | Medium | R-03 |
| Pilot tenant onboarding takes longer than expected due to setup complexity. | Open | Create onboarding playbook, checklist-driven setup, and a minimum required data template. Run one dry-run onboarding before pilot week. | Medium | 1 linked | Medium | R-02 |
| External connector APIs (Shopify/Meta/Google) change unexpectedly and break sync logic. | Open | Build connector adapters with contract tests, version pinning where possible, retry/backoff, and weekly connector health checks. Keep fallback/manual re-sync path ready. | High | 1 linked | Medium | R-01 |

## 05-Decisions

| Rationale | Chosen Option | Context | Decision | Date | Status | Decision ID |
| --- | --- | --- | --- | --- | --- | --- |
| Three gates prevent over-recommending and trust erosion: (1) change detection ensures a real signal exists, (2) delta gate ensures x* is actionably different from current state, (3) impact floor ensures projected improvement is worth surfacing. scipy.optimize finds the true continuous optimum rather than a discrete sweep approximation. LLM boundary ensures all numbers are deterministic and traceable to simulation output — eliminates hallucination risk on financial values. | Simulation-backed, event-driven recommendations with three-gate filter before any recommendation fires. Continuous mathematical optimizer (scipy.optimize) finds x* (true optimum) for all simulation domains. LLM narration layer generates words and urgency framing only — never generates numbers. All numerical outputs come exclusively from simulation payload. | Needed to define: (a) when recommendations fire — not on every sync cycle, only when a material signal is detected; (b) how the simulation optimizer works — continuous optimizer not discrete; (c) what role LLM plays — narration of evidence, not computation of numbers. Risk: over-recommending erodes trust. Risk: LLM-generated numbers create non-deterministic financial outputs. | Recommendation engine architecture: trigger model, simulation optimizer, and LLM narration boundary | 2026-06-02 | Active | D-12 |
| short reason | Go or No-Go | final launch gate review | Go/No-Go Launch Decision | 2026-08-14 | Active | D-11 |
| Prevents hardcoded-currency errors and supports multi-region tenants correctly. | Tenant base currency for thresholds and exposure checks. | Needed consistent financial threshold logic across geographies. | Currency handling rule | 2026-05-14 | Active | D-10 |
| Immediate practical control with auditability; ML suppression can come later. | Pattern-aware suppression rule-based (configurable threshold/window). | Needed a way to reduce repeated low-value recommendation noise. | Recommendation suppression behavior | 2026-05-14 | Active | D-09 |
| Managed services reduce operational burden and speed up delivery. | AWS Fargate + RDS + ElastiCache. | Needed low-ops deployment model for backend, DB, and queue/cache. | Infrastructure baseline | 2026-05-14 | Active | D-08 |
| Predictable outcomes, easier debugging, better explainability for business users. | Deterministic rule engine first; ML deferred. | Needed explainable recommendation logic for early trust. | Recommendation intelligence approach | 2026-05-14 | Active | D-07 |
| Mature ecosystem, robust app patterns, better long-term maintainability. | Next.js + TypeScript. | Needed a maintainable frontend with strong routing/type safety. | Frontend stack | 2026-05-14 | Active | D-06 |
| Reduces security risk and build time while preserving product-level permissions control. | Auth0/Clerk managed auth + internal RBAC. | Needed secure auth quickly without reinventing auth internals. | Authentication strategy | 2026-05-14 | Active | D-05 |
| Strong relational integrity, lower ops overhead, scalable for early stage. | PostgreSQL + shared DB with strict tenant_id isolation. | Needed reliable data integrity and practical multi-tenant setup. | Primary data/tenancy model | 2026-05-14 | Active | D-04 |
| Strong analytics ecosystem, fast API development, clean async support. | Python + FastAPI. | Needed a backend stack for analytics-heavy logic and APIs. | Backend language/framework | 2026-05-14 | Active | D-03 |
| Lower complexity and faster delivery than microservices at current stage. | Modular monolith first | Needed a delivery-friendly architecture for one founder and fast iteration. | Initial architecture style | 2026-05-02 | Active | D-02 |
| Keeps governance, trust, and auditability strong; reduces legal/operational risk. | Decision-intelligence only (no external action execution). | Needed to define what AlpMark will and will not do operationally. | Product action boundary | 2026-05-01 | Active | D-01 |

## 06-Launch Gates

| Gate Name | Verification Method | Category | Required for Launch | Status | Gate ID  |
| --- | --- | --- | --- | --- | --- |
| Go No-Go meeting completed and approved | Conduct formal Go/No-Go review with all gates reviewed. Decision logged in Decisions database as D-11 with rationale and date. | Operational | Yes | Not Ready | LG-12 |
| Accessibility WCAG 2.1 AA verified | Run automated accessibility scan on core flows. Manually review flagged items. No critical WCAG 2.1 AA violations remaining. | Compliance | Yes | Not Ready | LG-11 |
| Persona UAT at 80% unassisted completion | Run UAT sessions with at least one representative per persona. Score unassisted task completion rate. Minimum 80% required. | Product | Yes | Not Ready | LG-10 |
| Security audit complete | Complete security checklist: RBAC enforcement, secrets scan, TLS config scan, support access lifecycle, audit log immutability. No critical findings open. | Security | Yes | Not Ready | LG-09 |
| Pilot onboarding playbook ready | Review onboarding playbook document. Confirm all setup steps are covered, tested, and a dry-run onboarding has been completed successfully. | Product | Yes | Not Ready | LG-08 |
| Rollback procedure rehearsed | Execute a full rollback to previous application version on staging. Confirm service recovers correctly and procedure is documented. | Operational | Yes | Not Ready | LG-07 |
| Backup and restore tested | Execute RDS restore drill from latest daily snapshot. Confirm restore completes within RTO target of 8 hours and data loss within RPO of 24 hours. | Reliability | Yes | Not Ready | LG-06 |
| Observability dashboards live | Confirm Grafana dashboards and Sentry project active. Trigger test alert and verify it appears in both. | Operational | Yes | Not Ready | LG-05 |
| Alert SLA verified at 95% within 1 hour | Pull monthly alert pipeline report showing percentage of alerts emitted within 1 hour of detection. Target >= 95%. | Reliability | Yes | Not Ready | LG-04 |
| E2E recommendation flow works for 5 pilot tenants | Run Playwright E2E suite covering full recommendation lifecycle for each persona on staging environment. | Product | Yes | Not Ready | LG-03 |
| Tenant isolation tests pass 100% | Run automated tenant boundary integration test suite. Zero cross-tenant reads or writes allowed. | Security | Yes | Not Ready | LG-02 |
| All P0 tasks complete | Open Task kanban view filtered by Priority = P0 and Status != Done. All must show Done. | Operational | Yes | Not Ready | LG-01 |

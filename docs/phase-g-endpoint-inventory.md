# AlpMark Backend API Endpoint Inventory

**Phase G: Hardening & Traceability**  
**Generated**: 2026-06-20  
**Source**: [backend/app/main.py](../backend/app/main.py)

---

## Summary Statistics

- **Total Endpoints**: 178
- **Domains**: 14 (System, Auth, Tenants, Finance, Operations, Retention, Growth, Executive, Intelligence, Integrations, Admin, Support, Notifications, Roles)
- **Auth Types**: 
  - None (public): 7 endpoints
  - AuthDep (basic auth): 19 endpoints  
  - Permission-based (granular): 144 endpoints
  - SuperAdminDep (platform admin): 15 endpoints
  - Feature flag-gated: 13 endpoints

---

## Endpoint Matrix

### System & Health
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/health` | None | dict | System | Health check endpoint |
| GET | `/subscription-plans` | None | list[SubscriptionPlanResponse] | System | List all active subscription plans (public) |
| GET | `/subscription-plans/{slug}` | None | SubscriptionPlanResponse | System | Get subscription plan by slug (public) |
| GET | `/permissions` | AuthDep | PermissionCatalogResponse | System | Get catalog of all available permissions |
| GET | `/kpis` | AuthDep | KPICatalogResponse | System | Get catalog of all KPI metadata with optional domain filter |

### Auth & Users
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/auth/login` | None | LoginResponse | Auth | Authenticate user and return JWT token |
| POST | `/auth/forgot-password` | None | ForgotPasswordResponse | Auth | Initiate password reset flow |
| POST | `/auth/reset-password` | None | ResetPasswordResponse | Auth | Reset password using valid reset token |
| POST | `/auth/logout` | AuthDep | LogoutResponse | Auth | Logout current session by revoking JWT |
| POST | `/auth/logout-all` | AuthDep | LogoutResponse | Auth | Logout all sessions for user |
| GET | `/me/sessions` | AuthDep | SessionListResponse | Auth | Get all active sessions for current user |
| GET | `/users/me` | AuthDep | UserResponse | Auth | Get current authenticated user's info |
| GET | `/me/navigation` | AuthDep | NavigationMenuResponse | Navigation | Get persona-specific navigation menu with feature flag filtering |

### Tenants & Onboarding
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants` | SuperAdminDep | TenantCreateResponse | Admin | Create new tenant with default roles and rule thresholds |
| POST | `/tenants/{tenant_id}/invitations` | AdminMembersDep | UserInviteResponse | Admin | Invite user to tenant |
| POST | `/accounts/activate` | AuthDep | AccountActivationResponse | Admin | Activate account using invitation token |
| GET | `/tenants/{tenant_id}/onboarding-checklist` | AdminSettingsDep | OnboardingChecklistResponse | Admin | Get onboarding progress checklist |
| PATCH | `/tenants/{tenant_id}/members/{user_id}/role` | AdminRolesDep | MembershipResponse | Admin | Update member role |
| PATCH | `/tenants/{tenant_id}/members/{user_id}/deactivate` | AdminMembersDep | MembershipResponse | Admin | Deactivate tenant member |
| GET | `/tenants/{tenant_id}/billing-seats` | AdminBillingDep | BillingSeatResponse | Admin | Get billing and seat usage info |
| PATCH | `/tenants/{tenant_id}/billing-seats` | AdminBillingDep | BillingSeatResponse | Admin | Update billing plan, cycle, status, or seat limit |
| GET | `/tenants/{tenant_id}/locale` | AdminSettingsDep | TenantLocaleResponse | Admin | Get tenant's base currency and locale settings |
| PATCH | `/tenants/{tenant_id}/locale` | AdminSettingsDep | TenantLocaleResponse | Admin | Update base_currency and/or locale |

### Super-Admin: Subscription Plans
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/admin/subscription-plans` | SuperAdminDep | SubscriptionPlanResponse | Admin | Create new subscription plan |
| PATCH | `/admin/subscription-plans/{plan_id}` | SuperAdminDep | SubscriptionPlanResponse | Admin | Update subscription plan |
| DELETE | `/admin/subscription-plans/{plan_id}` | SuperAdminDep | Response (204) | Admin | Deactivate subscription plan |

### Super-Admin: Feature Flags
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/features` | AuthDep | list[TenantFeatureResponse] | Admin | Get all feature flags for tenant with enabled status |
| GET | `/admin/feature-flags` | SuperAdminDep | list[FeatureFlagResponse] | Admin | List all feature flags |
| POST | `/admin/feature-flags` | SuperAdminDep | FeatureFlagResponse | Admin | Create new feature flag |
| PATCH | `/admin/feature-flags/{flag_id}` | SuperAdminDep | FeatureFlagResponse | Admin | Update feature flag |
| POST | `/admin/tenants/{tenant_id}/features/toggle` | SuperAdminDep | dict | Admin | Toggle feature flag for tenant |

### Super-Admin: Tenant Management
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/admin/tenants` | SuperAdminDep | AdminTenantListResponse | Admin | List all tenants with pagination and filters |
| GET | `/admin/tenants/{tenant_id}` | SuperAdminDep | AdminTenantResponse | Admin | Get single tenant details |
| PATCH | `/admin/tenants/{tenant_id}` | SuperAdminDep | AdminTenantResponse | Admin | Update tenant details |
| PATCH | `/admin/tenants/{tenant_id}/status` | SuperAdminDep | AdminTenantResponse | Admin | Suspend or activate tenant |

### Super-Admin: Platform Metrics
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/admin/platform/metrics` | SuperAdminDep | PlatformMetricsResponse | Admin | Platform-wide metrics dashboard (tenants, users, subscriptions, features, integrations) |
| GET | `/admin/platform/connectors` | SuperAdminDep | ConnectorAvailabilityResponse | Admin | Platform-wide connector availability tracking |

### Notification Routing & Privacy
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/notification-routing` | AdminSettingsDep | NotificationRoutingResponse | Admin | Get notification routing configuration |
| PUT | `/tenants/{tenant_id}/notification-routing` | AdminSettingsDep | NotificationRoutingResponse | Admin | Upsert notification routing rules |
| POST | `/tenants/{tenant_id}/privacy-requests` | AdminAuditDep | PrivacyRequestResponse | Admin | Create privacy request (export/delete) |
| GET | `/tenants/{tenant_id}/privacy-requests` | AdminAuditDep | list[PrivacyRequestResponse] | Admin | List privacy requests |
| PATCH | `/tenants/{tenant_id}/privacy-requests/{request_id}` | AdminAuditDep | PrivacyRequestResponse | Admin | Update privacy request status |

### Integrations: Shopify
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/connectors/shopify/oauth/start` | AdminIntegrationsDep | ShopifyOAuthStartResponse | Integrations | Start Shopify OAuth flow |
| POST | `/tenants/{tenant_id}/connectors/shopify/oauth/callback` | AdminIntegrationsDep | ConnectorResponse | Integrations | Complete Shopify OAuth callback |

### Integrations: Meta
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/connectors/meta/oauth/start` | AdminIntegrationsDep | MetaOAuthStartResponse | Integrations | Start Meta OAuth flow |
| POST | `/tenants/{tenant_id}/connectors/meta/oauth/callback` | AdminIntegrationsDep | ConnectorResponse | Integrations | Complete Meta OAuth callback |

### Integrations: Google Ads
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/connectors/google_ads/oauth/start` | AdminIntegrationsDep | GoogleAdsOAuthStartResponse | Integrations | Start Google Ads OAuth flow |
| POST | `/tenants/{tenant_id}/connectors/google_ads/oauth/callback` | AdminIntegrationsDep | ConnectorResponse | Integrations | Complete Google Ads OAuth callback |

### Integrations: API Key & Management
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/connectors/{source}/api-key` | AdminIntegrationsDep | ConnectorResponse | Integrations | Connect source with API key (Klaviyo, Amazon Ads, TikTok, custom) |
| POST | `/tenants/{tenant_id}/connectors/{source}/reauthorize` | AdminIntegrationsDep | ConnectorResponse | Integrations | Reauthorize OAuth connector |
| POST | `/tenants/{tenant_id}/connectors/{source}/resync` | AdminIntegrationsDep | ConnectorManualResyncResponse | Integrations | Trigger manual resync for connector |
| GET | `/tenants/{tenant_id}/connectors/{source}/status` | AdminIntegrationsDep | ConnectorIntegrationStatusResponse | Integrations | Get connector integration status with sync metrics |
| GET | `/tenants/{tenant_id}/workspace-health` | AdminIntegrationsDep | WorkspaceHealthResponse | Integrations | Get aggregated health status for all connectors |

### Support Tickets
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/support-tickets` | SuperAdminDep | SupportTicketResponse | Support | Create new support ticket |
| GET | `/support-tickets` | SuperAdminDep | SupportTicketListResponse | Support | List support tickets with filters |
| GET | `/support-tickets/{ticket_id}` | SuperAdminDep | SupportTicketResponse | Support | Get single support ticket |
| PATCH | `/support-tickets/{ticket_id}` | SuperAdminDep | SupportTicketResponse | Support | Update support ticket |
| PATCH | `/support-tickets/{ticket_id}/close` | SuperAdminDep | SupportTicketResponse | Support | Close support ticket with resolution |

### Notifications & Preferences
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/user-notification-preferences` | AuthDep | UserNotificationPreferenceResponse | Notifications | Create user notification preference |
| GET | `/user-notification-preferences` | AuthDep | UserNotificationPreferenceListResponse | Notifications | List user's notification preferences |
| PATCH | `/user-notification-preferences/{preference_id}` | AuthDep | UserNotificationPreferenceResponse | Notifications | Update user notification preference |
| DELETE | `/user-notification-preferences/{preference_id}` | AuthDep | Response (204) | Notifications | Delete user notification preference |
| POST | `/notifications` | SuperAdminDep | NotificationResponse | Notifications | Create notification (internal use) |
| GET | `/notifications` | AuthDep | NotificationListResponse | Notifications | List user notifications with filters |
| PATCH | `/notifications/{notification_id}/read` | AuthDep | NotificationResponse | Notifications | Mark notification as read |
| PATCH | `/notifications/{notification_id}/dismiss` | AuthDep | NotificationResponse | Notifications | Mark notification as dismissed |

### Finance: Cost Drivers & Margin Drift
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/finance/cost-drivers` | FinanceViewDep | CostDriverListResponse | Finance | Get latest cost driver snapshots |
| GET | `/tenants/{tenant_id}/finance/margin-drift-thresholds` | FinanceViewDep | MarginDriftThresholdListResponse | Finance | List margin drift thresholds |
| POST | `/tenants/{tenant_id}/finance/margin-drift-thresholds` | FinanceEditCostsDep | MarginDriftThresholdResponse | Finance | Create margin drift threshold |
| PUT | `/tenants/{tenant_id}/finance/margin-drift-thresholds/{threshold_id}` | FinanceEditCostsDep | MarginDriftThresholdResponse | Finance | Update margin drift threshold |
| DELETE | `/tenants/{tenant_id}/finance/margin-drift-thresholds/{threshold_id}` | FinanceEditCostsDep | Response (204) | Finance | Deactivate margin drift threshold |
| GET | `/tenants/{tenant_id}/finance/margin-drift` | FinanceViewDep | MarginDriftListResponse | Finance | Get latest margin drift snapshots |

### Finance: Cost Inputs & Versioning
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/finance/cost-inputs/{input_id}` | FinanceViewDep | CostInputResponse | Finance | Get single cost input |
| GET | `/tenants/{tenant_id}/finance/cost-inputs` | FinanceViewDep | CostInputListResponse | Finance | List cost inputs with filters |
| POST | `/tenants/{tenant_id}/finance/cost-inputs` | FinanceEditCostsDep | CostInputResponse | Finance | Create cost input with version history |
| PUT | `/tenants/{tenant_id}/finance/cost-inputs/{input_id}` | FinanceEditCostsDep | CostInputResponse | Finance | Update cost input (triggers confirmation for high-impact) |
| POST | `/tenants/{tenant_id}/finance/cost-inputs/{input_id}/confirm` | FinanceEditCostsDep | Response (204) | Finance | Confirm pending cost input |
| POST | `/tenants/{tenant_id}/finance/cost-inputs/{input_id}/reject` | FinanceEditCostsDep | Response (204) | Finance | Reject pending cost input confirmation |
| DELETE | `/tenants/{tenant_id}/finance/cost-inputs/{input_id}` | FinanceEditCostsDep | Response (204) | Finance | Deactivate cost input |
| GET | `/tenants/{tenant_id}/finance/cost-inputs/{input_id}/history` | FinanceViewDep | CostInputHistoryResponse | Finance | Get cost input version history |
| POST | `/tenants/{tenant_id}/finance/restatements` | FinanceEditCostsDep | HistoricalRestatementResponse | Finance | Restate historical margin under prior vs new cost versions |

### Inventory: Risk & Thresholds
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/inventory/risk` | OperationsViewDep | InventoryRiskListResponse | Operations | Get latest inventory risk snapshots |
| GET | `/tenants/{tenant_id}/inventory/risk-thresholds` | OperationsViewDep | InventoryRiskThresholdListResponse | Operations | List inventory risk thresholds |
| POST | `/tenants/{tenant_id}/inventory/risk-thresholds` | OperationsInventoryDep | InventoryRiskThresholdResponse | Operations | Create inventory risk threshold |
| PUT | `/tenants/{tenant_id}/inventory/risk-thresholds/{threshold_id}` | OperationsInventoryDep | InventoryRiskThresholdResponse | Operations | Update inventory risk threshold |
| DELETE | `/tenants/{tenant_id}/inventory/risk-thresholds/{threshold_id}` | OperationsInventoryDep | Response (204) | Operations | Deactivate inventory risk threshold |

### Inventory: Warehouses & Logistics
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/inventory/warehouses` | OperationsViewDep | MultiWarehouseInventoryResponse | Operations | List inventory health across all warehouses/locations |
| GET | `/tenants/{tenant_id}/inventory/skus/{sku_id}/stockout-impact` | OperationsViewDep | StockoutImpactResponse | Operations | Get estimated revenue and repeat purchase impact of SKU stockout |
| GET | `/tenants/{tenant_id}/inventory/skus/{sku_id}/logistics-costs` | OperationsViewDep | LogisticsCostBreakdownResponse | Operations | Get estimated logistics cost breakdown for a SKU |

### Operations: Operational Impact
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/operational/impact` | OperationsViewDep | OperationalImpactListResponse | Operations | List operational impact snapshots |

### Recommendations
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/recommendations` | IntelRecommendationsViewDep | RecommendationListResponse | Intelligence | List recommendations with filters (domain, status, gap_flag, has_outcome) |
| GET | `/tenants/{tenant_id}/recommendations/{recommendation_id}` | IntelRecommendationsViewDep | RecommendationDetailResponse | Intelligence | Get recommendation with full simulation provenance |
| GET | `/tenants/{tenant_id}/recommendations/{recommendation_id}/simulations` | IntelSimulationsViewDep | SimulationListResponse | Intelligence | List all simulations spawned from a recommendation |
| PATCH | `/tenants/{tenant_id}/recommendations/{recommendation_id}/status` | IntelRecommendationsReviewDep | RecommendationResponse | Intelligence | Transition recommendation status (lifecycle state machine) |
| POST | `/tenants/{tenant_id}/recommendations/{recommendation_id}/simulate` | IntelSimulationsRunDep | RecommendationSimulationLaunchResponse | Intelligence | Launch simulation pre-populated from recommendation |
| POST | `/tenants/{tenant_id}/recommendations/{recommendation_id}/narrate` | IntelRecommendationsViewDep | NarrationResponse | Intelligence | Generate LLM narration for recommendation |

### Recommendations: Suppression & Delegation
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/recommendation-suppressions` | AdminSettingsDep | SuppressionStateListResponse | Intelligence | List all suppression states |
| POST | `/tenants/{tenant_id}/recommendation-suppressions/{rule_id}/override` | AdminSettingsDep | SuppressionStateResponse | Intelligence | Lift active suppression window for a rule |
| POST | `/tenants/{tenant_id}/delegation-rules` | AdminSettingsDep | DelegationRuleResponse | Intelligence | Create delegation rule for approval authority |
| GET | `/tenants/{tenant_id}/delegation-rules` | AdminSettingsDep | DelegationRuleListResponse | Intelligence | List delegation rules |
| POST | `/tenants/{tenant_id}/delegation-rules/{delegation_id}/revoke` | AdminSettingsDep | DelegationRuleResponse | Intelligence | Revoke active delegation rule |

### Rule Thresholds
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/rule-thresholds` | AdminSettingsDep | RuleThresholdListResponse | Intelligence | List all rule thresholds |
| PATCH | `/tenants/{tenant_id}/rule-thresholds/{rule_id}` | AdminSettingsDep | RuleThresholdResponse | Intelligence | Update threshold value for specific rule |

### Analysis Views
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/analysis-views` | IntelInsightsViewDep | SavedAnalysisViewResponse | Intelligence | Create saved analysis view |
| GET | `/tenants/{tenant_id}/analysis-views` | IntelInsightsViewDep | SavedAnalysisViewListResponse | Intelligence | List saved analysis views |
| GET | `/tenants/{tenant_id}/analysis-views/{view_id}` | IntelInsightsViewDep | SavedAnalysisViewResponse | Intelligence | Get specific saved analysis view |
| DELETE | `/tenants/{tenant_id}/analysis-views/{view_id}` | IntelInsightsViewDep | Response (204) | Intelligence | Delete saved analysis view |
| POST | `/tenants/{tenant_id}/analysis-views/{view_id}/share` | IntelInsightsViewDep | AnalysisViewShareListResponse | Intelligence | Share analysis view with recipients |
| GET | `/tenants/{tenant_id}/analysis-views/{view_id}/shares` | IntelInsightsViewDep | AnalysisViewShareListResponse | Intelligence | List all shares for analysis view |
| GET | `/tenants/{tenant_id}/analysis-views/{view_id}/export` | IntelInsightsViewDep | Response (file) | Intelligence | Download exported analysis view as CSV or JSON |
| GET | `/saved-views/{one_time_token}` | None | SavedAnalysisViewResponse | Intelligence | Public guest access to shared view via one-time token |

### Annotations
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/analysis-views/{view_id}/annotations` | IntelInsightsViewDep | AnnotationResponse | Intelligence | Create annotation on analysis view |
| GET | `/tenants/{tenant_id}/analysis-views/{view_id}/annotations` | IntelInsightsViewDep | AnnotationListResponse | Intelligence | List annotations for analysis view |
| DELETE | `/tenants/{tenant_id}/analysis-views/{view_id}/annotations/{annotation_id}` | IntelInsightsViewDep | Response (204) | Intelligence | Delete annotation |

### Cohorts
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/cohorts` | RetentionViewDep | CohortSnapshotResponse | Retention | Create cohort snapshot for comparison |
| POST | `/tenants/{tenant_id}/cohorts/compare` | RetentionAnalyzeDep | CohortComparisonResponse | Retention | Compare cohorts side-by-side |
| GET | `/tenants/{tenant_id}/retention/acquisition-context` | RetentionViewDep | AcquisitionContextResponse | Retention | Get acquisition context for retention analysis (read-only) |

### Custom Segments
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/retention/custom-segments` | RetentionViewDep + RequireCustomSegments | CustomSegmentResponse | Retention | Create custom customer segment |
| GET | `/tenants/{tenant_id}/retention/custom-segments` | RetentionViewDep + RequireCustomSegments | CustomSegmentListResponse | Retention | List custom segments |
| GET | `/tenants/{tenant_id}/retention/custom-segments/{segment_id}` | RetentionViewDep + RequireCustomSegments | CustomSegmentResponse | Retention | Get custom segment by ID |
| PUT | `/tenants/{tenant_id}/retention/custom-segments/{segment_id}` | RetentionViewDep + RequireCustomSegments | CustomSegmentResponse | Retention | Update custom segment |
| DELETE | `/tenants/{tenant_id}/retention/custom-segments/{segment_id}` | RetentionViewDep + RequireCustomSegments | Response (204) | Retention | Delete custom segment |

### Alerts: Thresholds & Recipients
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/alerts/thresholds` | IntelAlertsManageDep | AlertThresholdResponse | Intelligence | Create alert threshold |
| GET | `/tenants/{tenant_id}/alerts/thresholds` | IntelAlertsManageDep | AlertThresholdListResponse | Intelligence | List alert thresholds |
| GET | `/tenants/{tenant_id}/alerts/thresholds/{threshold_id}` | IntelAlertsManageDep | AlertThresholdResponse | Intelligence | Get specific alert threshold |
| PUT | `/tenants/{tenant_id}/alerts/thresholds/{threshold_id}` | IntelAlertsManageDep | AlertThresholdResponse | Intelligence | Update alert threshold |
| DELETE | `/tenants/{tenant_id}/alerts/thresholds/{threshold_id}` | IntelAlertsManageDep | Response (204) | Intelligence | Delete alert threshold |
| POST | `/tenants/{tenant_id}/alerts/recipients` | IntelAlertsManageDep | AlertRecipientResponse | Intelligence | Create alert recipient |
| GET | `/tenants/{tenant_id}/alerts/recipients` | IntelAlertsManageDep | AlertRecipientListResponse | Intelligence | List alert recipients |
| GET | `/tenants/{tenant_id}/alerts/recipients/{recipient_id}` | IntelAlertsManageDep | AlertRecipientResponse | Intelligence | Get specific alert recipient |
| PUT | `/tenants/{tenant_id}/alerts/recipients/{recipient_id}` | IntelAlertsManageDep | AlertRecipientResponse | Intelligence | Update alert recipient |
| DELETE | `/tenants/{tenant_id}/alerts/recipients/{recipient_id}` | IntelAlertsManageDep | Response (204) | Intelligence | Delete alert recipient |

### Alerts: Escalation & Acknowledgement
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/alerts/acknowledge` | IntelAlertsManageDep | AlertAcknowledgementResponse | Intelligence | Acknowledge alert |
| POST | `/tenants/{tenant_id}/alerts/dismiss` | IntelAlertsManageDep | AlertDismissalResponse | Intelligence | Dismiss alert with optional reason |
| POST | `/tenants/{tenant_id}/alerts/escalation-rules` | IntelAlertsManageDep | EscalationRuleResponse | Intelligence | Create escalation rule |
| GET | `/tenants/{tenant_id}/alerts/escalation-rules` | IntelAlertsManageDep | EscalationRuleListResponse | Intelligence | List escalation rules |
| GET | `/tenants/{tenant_id}/alerts/escalation-rules/{rule_id}` | IntelAlertsManageDep | EscalationRuleResponse | Intelligence | Get specific escalation rule |
| PUT | `/tenants/{tenant_id}/alerts/escalation-rules/{rule_id}` | IntelAlertsManageDep | EscalationRuleResponse | Intelligence | Update escalation rule |
| DELETE | `/tenants/{tenant_id}/alerts/escalation-rules/{rule_id}` | IntelAlertsManageDep | Response (204) | Intelligence | Delete escalation rule |

### Alerts: History & Audit
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/alerts/history` | IntelAlertsManageDep | AlertEventListResponse | Intelligence | List alert events with pagination and filtering |
| GET | `/tenants/{tenant_id}/alerts/{alert_id}/history` | IntelAlertsManageDep | AlertHistoryResponse | Intelligence | Get complete immutable history for specific alert |

### Email Delivery Tracking
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/email-delivery/history` | AdminAuditDep | EmailDeliveryListResponse | Admin | List email delivery records with filtering |
| GET | `/tenants/{tenant_id}/email-delivery/alerts/{alert_id}/history` | AdminAuditDep | EmailDeliveryHistoryResponse | Admin | Get complete email delivery history for specific alert |

### Simulations: Domain-Specific
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/simulations/growth` | IntelSimulationsRunDep + RequireSimulations | SimulationResponse | Intelligence | Simulate growth channel budget reallocation |
| POST | `/tenants/{tenant_id}/simulations/retention` | IntelSimulationsRunDep + RequireSimulations | SimulationResponse | Intelligence | Simulate retention intervention |
| POST | `/tenants/{tenant_id}/simulations/finance` | IntelSimulationsRunDep + RequireSimulations | SimulationResponse | Intelligence | Simulate cost input changes |
| POST | `/tenants/{tenant_id}/simulations/operations` | IntelSimulationsRunDep + RequireSimulations | SimulationResponse | Intelligence | Simulate inventory reorder policy changes |
| POST | `/tenants/{tenant_id}/simulations/executive` | IntelSimulationsRunDep + RequireSimulations | SimulationResponse | Intelligence | Simulate strategic what-if scenarios |

### Simulations: Management & Comparison
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/simulations` | IntelSimulationsViewDep + RequireSimulations | SimulationListResponse | Intelligence | List all simulations with pagination |
| GET | `/tenants/{tenant_id}/simulations/{simulation_id}` | IntelSimulationsViewDep + RequireSimulations | SimulationDetailResponse | Intelligence | Get simulation with all scenarios |
| GET | `/tenants/{tenant_id}/simulations/{simulation_id}/chart-data` | IntelSimulationsViewDep + RequireSimulations | SimulationChartDataResponse | Intelligence | Get chart-ready data for frontend visualization |
| GET | `/tenants/{tenant_id}/simulations/recommendations/{recommendation_id}` | IntelSimulationsViewDep + RequireSimulations | SimulationResponse | Intelligence | Get simulation generated for specific recommendation |
| POST | `/tenants/{tenant_id}/simulations/compare` | IntelSimulationsViewDep + RequireSimulations | dict | Intelligence | Compare multiple simulations side-by-side |
| PATCH | `/tenants/{tenant_id}/simulations/{simulation_id}` | IntelSimulationsViewDep + RequireSimulations | SimulationResponse | Intelligence | Update simulation name/description |
| POST | `/tenants/{tenant_id}/simulations/{simulation_id}/duplicate` | IntelSimulationsViewDep + RequireSimulations | SimulationDuplicateResponse | Intelligence | Duplicate simulation with all scenarios |
| DELETE | `/tenants/{tenant_id}/simulations/{simulation_id}` | IntelSimulationsViewDep + RequireSimulations | Response (204) | Intelligence | Soft delete simulation |

### Simulations: Export & Sharing
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| POST | `/tenants/{tenant_id}/simulations/{simulation_id}/export` | IntelSimulationsViewDep + RequireSimulations | StreamingResponse | Intelligence | Generate and download simulation export (PDF or CSV) |
| POST | `/tenants/{tenant_id}/simulations/{simulation_id}/share` | IntelSimulationsViewDep + RequireSimulations | ExportShareResponse | Intelligence | Share simulation export with recipient |
| GET | `/tenants/{tenant_id}/exports/shared` | IntelSimulationsViewDep | ExportShareListResponse | Intelligence | List simulation exports shared with current user |
| DELETE | `/tenants/{tenant_id}/exports/{share_id}/revoke` | IntelSimulationsViewDep | ExportShareResponse | Intelligence | Revoke export share |
| POST | `/tenants/{tenant_id}/exports/{share_id}/generate-link` | IntelSimulationsViewDep | GeneratedExportLinkResponse | Intelligence | Generate signed download link for export share |
| GET | `/exports/download/{token}` | None | StreamingResponse | Intelligence | Download export file using signed download link |

### Dashboards: Executive
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/executive/overview` | ExecutiveViewDep | ExecutiveOverviewResponse | Executive | Get executive overview dashboard with key metrics |
| GET | `/tenants/{tenant_id}/executive/trend` | ExecutiveViewDep | ExecutiveTrendResponse | Executive | Get executive KPI trend (time-series) |

### Dashboards: Growth
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/growth/dashboard` | GrowthViewDep | GrowthDashboardResponse | Growth | Get growth dashboard with channel and campaign metrics |
| GET | `/tenants/{tenant_id}/growth/trend` | GrowthViewDep | GrowthTrendResponse | Growth | Get growth channel trends (time-series) |

### Dashboards: Retention
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/retention/dashboard` | RetentionViewDep | RetentionDashboardResponse | Retention | Get retention dashboard with metrics |
| GET | `/tenants/{tenant_id}/retention/trend` | RetentionViewDep | RetentionTrendResponse | Retention | Get retention metrics trend (time-series) |

### Trends: Finance & Operations
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/tenants/{tenant_id}/finance/cost-drivers/trend` | FinanceViewDep | CostDriverTrendResponse | Finance | Get cost driver trend (time-series) |
| GET | `/tenants/{tenant_id}/finance/margin-drift/trend` | FinanceViewDep | MarginDriftTrendResponse | Finance | Get margin drift trend (time-series) |
| GET | `/tenants/{tenant_id}/operations/inventory-risk/trend` | OperationsViewDep | InventoryRiskTrendResponse | Operations | Get inventory risk trend (time-series) |
| GET | `/tenants/{tenant_id}/operations/operational-impact/trend` | OperationsViewDep | OperationalImpactTrendResponse | Operations | Get operational impact trend (time-series) |

### Roles & Permissions
| Method | Path | Auth | Response Model | Domain | Purpose |
|--------|------|------|----------------|--------|---------|
| GET | `/roles` | AuthDep | RoleListResponse | Admin | Get all roles for tenant (system and custom) |
| POST | `/roles` | AuthDep | RoleResponse | Admin | Create custom role for tenant |
| GET | `/roles/{role_id}` | AuthDep | RoleResponse | Admin | Get role details by ID |
| PUT | `/roles/{role_id}` | AuthDep | RoleResponse | Admin | Update custom role (system roles cannot be modified) |
| DELETE | `/roles/{role_id}` | AuthDep | Response (204) | Admin | Delete custom role (system roles cannot be deleted) |

---

## Architecture Notes

### Permission Model
The API uses a granular permission-based access control system aligned to 8 personas:
1. Executive Owner
2. Brand Admin
3. Growth & Performance Manager
4. Retention & CRM Manager
5. Finance Controller
6. Operations & Inventory Manager
7. Viewer
8. AlpMark Support Operator (internal)

### Feature Flags
13 endpoints are gated behind feature flags:
- `custom_segments`: Retention custom segment endpoints
- `simulations`: All simulation creation/management endpoints

### Tenant Isolation
All tenant-scoped endpoints include `{tenant_id}` in path and enforce:
- User must be a member of the tenant
- User must have required permissions for the action
- Soft-deleted records are filtered by default

### Audit Trail
Key actions generate immutable audit events:
- Alert acknowledgements/dismissals
- Recommendation status transitions
- Cost input confirmations/rejections
- Privacy request actions

---

## Frontend Usage Map

To be completed: Map each endpoint to the frontend screens/components that consume it.

**Next Step**: Create endpoint-to-screen mapping matrix showing which Next.js pages/components call which API endpoints.

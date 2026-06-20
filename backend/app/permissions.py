"""Permission registry for RBAC system.

This module defines all available permissions in the system.
Permissions follow the pattern: <domain>.<action>

Domains:
- admin: Administrative functions (tenant management, billing, members)
- executive: Executive-level intelligence and strategic decisions
- growth: Acquisition and media efficiency
- retention: Customer retention and CRM
- finance: Financial operations and cost management
- operations: Inventory and operational management
- intel: Intelligence features (recommendations, simulations, insights)
"""

from typing import Final

# Administrative permissions (Brand Admin persona)
ADMIN_MEMBERS: Final[str] = "admin.members"
ADMIN_ROLES: Final[str] = "admin.roles"
ADMIN_BILLING: Final[str] = "admin.billing"
ADMIN_INTEGRATIONS: Final[str] = "admin.integrations"
ADMIN_SETTINGS: Final[str] = "admin.settings"
ADMIN_AUDIT: Final[str] = "admin.audit"

# Executive permissions (Executive Owner persona)
EXECUTIVE_VIEW: Final[str] = "executive.view"
EXECUTIVE_TARGETS: Final[str] = "executive.targets"
EXECUTIVE_APPROVE: Final[str] = "executive.approve"
EXECUTIVE_SIMULATE: Final[str] = "executive.simulate"

# Growth permissions (Growth & Performance Manager persona)
GROWTH_VIEW: Final[str] = "growth.view"
GROWTH_ANALYZE: Final[str] = "growth.analyze"
GROWTH_SIMULATE: Final[str] = "growth.simulate"

# Retention permissions (Retention & CRM Manager persona)
RETENTION_VIEW: Final[str] = "retention.view"
RETENTION_ANALYZE: Final[str] = "retention.analyze"
RETENTION_SIMULATE: Final[str] = "retention.simulate"

# Finance permissions (Finance Controller persona)
FINANCE_VIEW: Final[str] = "finance.view"
FINANCE_EDIT_COSTS: Final[str] = "finance.edit_costs"
FINANCE_ANALYZE: Final[str] = "finance.analyze"

# Operations permissions (Operations & Inventory Manager persona)
OPERATIONS_VIEW: Final[str] = "operations.view"
OPERATIONS_INVENTORY: Final[str] = "operations.inventory"
OPERATIONS_ANALYZE: Final[str] = "operations.analyze"

# Intelligence permissions (shared across personas)
INTEL_RECOMMENDATIONS_VIEW: Final[str] = "intel.recommendations.view"
INTEL_RECOMMENDATIONS_REVIEW: Final[str] = "intel.recommendations.review"
INTEL_RECOMMENDATIONS_APPROVE: Final[str] = "intel.recommendations.approve"
INTEL_SIMULATIONS_RUN: Final[str] = "intel.simulations.run"
INTEL_SIMULATIONS_VIEW: Final[str] = "intel.simulations.view"
INTEL_INSIGHTS_VIEW: Final[str] = "intel.insights.view"
INTEL_ALERTS_MANAGE: Final[str] = "intel.alerts.manage"

# All permissions registry
ALL_PERMISSIONS: Final[list[str]] = [
    # Admin
    ADMIN_MEMBERS,
    ADMIN_ROLES,
    ADMIN_BILLING,
    ADMIN_INTEGRATIONS,
    ADMIN_SETTINGS,
    ADMIN_AUDIT,
    # Executive
    EXECUTIVE_VIEW,
    EXECUTIVE_TARGETS,
    EXECUTIVE_APPROVE,
    EXECUTIVE_SIMULATE,
    # Growth
    GROWTH_VIEW,
    GROWTH_ANALYZE,
    GROWTH_SIMULATE,
    # Retention
    RETENTION_VIEW,
    RETENTION_ANALYZE,
    RETENTION_SIMULATE,
    # Finance
    FINANCE_VIEW,
    FINANCE_EDIT_COSTS,
    FINANCE_ANALYZE,
    # Operations
    OPERATIONS_VIEW,
    OPERATIONS_INVENTORY,
    OPERATIONS_ANALYZE,
    # Intelligence
    INTEL_RECOMMENDATIONS_VIEW,
    INTEL_RECOMMENDATIONS_REVIEW,
    INTEL_RECOMMENDATIONS_APPROVE,
    INTEL_SIMULATIONS_RUN,
    INTEL_SIMULATIONS_VIEW,
    INTEL_INSIGHTS_VIEW,
    INTEL_ALERTS_MANAGE,
]

# Permission descriptions for catalog endpoint
PERMISSION_DESCRIPTIONS: Final[dict[str, str]] = {
    # Admin
    ADMIN_MEMBERS: "Manage tenant members (invite, remove, update roles)",
    ADMIN_ROLES: "Manage custom roles and permissions",
    ADMIN_BILLING: "View and manage billing, subscription, and invoices",
    ADMIN_INTEGRATIONS: "Configure and manage data source integrations",
    ADMIN_SETTINGS: "Manage tenant settings and preferences",
    ADMIN_AUDIT: "View audit logs and security events",
    # Executive
    EXECUTIVE_VIEW: "View executive dashboards and KPI summaries",
    EXECUTIVE_TARGETS: "Set and update business targets and thresholds",
    EXECUTIVE_APPROVE: "Approve strategic recommendations",
    EXECUTIVE_SIMULATE: "Run strategic simulations",
    # Growth
    GROWTH_VIEW: "View acquisition and media efficiency metrics",
    GROWTH_ANALYZE: "Analyze channel/campaign performance and trends",
    GROWTH_SIMULATE: "Run growth and media spend simulations",
    # Retention
    RETENTION_VIEW: "View retention, cohort, and CRM metrics",
    RETENTION_ANALYZE: "Analyze retention trends and cohort behavior",
    RETENTION_SIMULATE: "Run retention and CRM simulations",
    # Finance
    FINANCE_VIEW: "View financial metrics and contribution margin",
    FINANCE_EDIT_COSTS: "Edit cost inputs and COGS data",
    FINANCE_ANALYZE: "Analyze profitability and margin trends",
    # Operations
    OPERATIONS_VIEW: "View inventory and operational metrics",
    OPERATIONS_INVENTORY: "Manage inventory risk thresholds",
    OPERATIONS_ANALYZE: "Analyze operational efficiency and risks",
    # Intelligence
    INTEL_RECOMMENDATIONS_VIEW: "View all recommendations",
    INTEL_RECOMMENDATIONS_REVIEW: "Review and comment on recommendations",
    INTEL_RECOMMENDATIONS_APPROVE: "Approve or reject recommendations",
    INTEL_SIMULATIONS_RUN: "Create and run simulations",
    INTEL_SIMULATIONS_VIEW: "View simulation results and history",
    INTEL_INSIGHTS_VIEW: "View insights and analysis views",
    INTEL_ALERTS_MANAGE: "Configure and manage alert settings",
}


def get_system_role_permissions(role_name: str) -> list[str]:
    """Get default permissions for system roles based on personas.
    
    Args:
        role_name: Name of the system role
        
    Returns:
        List of permission strings for that role
    """
    role_permissions = {
        "brand_admin": [
            # Admin domain - full control
            ADMIN_MEMBERS,
            ADMIN_ROLES,
            ADMIN_BILLING,
            ADMIN_INTEGRATIONS,
            ADMIN_SETTINGS,
            ADMIN_AUDIT,
            # No intelligence permissions - admin is operations only
        ],
        "executive_owner": [
            # Executive domain
            EXECUTIVE_VIEW,
            EXECUTIVE_TARGETS,
            EXECUTIVE_APPROVE,
            EXECUTIVE_SIMULATE,
            # Intelligence - strategic level
            INTEL_RECOMMENDATIONS_VIEW,
            INTEL_RECOMMENDATIONS_APPROVE,
            INTEL_SIMULATIONS_RUN,
            INTEL_SIMULATIONS_VIEW,
            INTEL_INSIGHTS_VIEW,
            INTEL_ALERTS_MANAGE,
        ],
        "growth_performance_manager": [
            # Growth domain
            GROWTH_VIEW,
            GROWTH_ANALYZE,
            GROWTH_SIMULATE,
            # Intelligence - growth specific
            INTEL_RECOMMENDATIONS_VIEW,
            INTEL_RECOMMENDATIONS_REVIEW,
            INTEL_SIMULATIONS_RUN,
            INTEL_SIMULATIONS_VIEW,
            INTEL_INSIGHTS_VIEW,
            INTEL_ALERTS_MANAGE,
        ],
        "retention_crm_manager": [
            # Retention domain
            RETENTION_VIEW,
            RETENTION_ANALYZE,
            RETENTION_SIMULATE,
            # Intelligence - retention specific
            INTEL_RECOMMENDATIONS_VIEW,
            INTEL_RECOMMENDATIONS_REVIEW,
            INTEL_SIMULATIONS_RUN,
            INTEL_SIMULATIONS_VIEW,
            INTEL_INSIGHTS_VIEW,
            INTEL_ALERTS_MANAGE,
        ],
        "finance_controller": [
            # Finance domain
            FINANCE_VIEW,
            FINANCE_EDIT_COSTS,
            FINANCE_ANALYZE,
            # Cross-functional view access for financial analysis
            EXECUTIVE_VIEW,  # View executive overview for business health
            GROWTH_VIEW,  # View growth metrics to understand revenue drivers
            RETENTION_VIEW,  # View retention metrics to understand CLV
            # Intelligence - finance specific
            INTEL_RECOMMENDATIONS_VIEW,
            INTEL_RECOMMENDATIONS_REVIEW,
            INTEL_INSIGHTS_VIEW,
        ],
        "operations_inventory_manager": [
            # Operations domain
            OPERATIONS_VIEW,
            OPERATIONS_INVENTORY,
            OPERATIONS_ANALYZE,
            # ALL other domains for comprehensive testing
            ADMIN_MEMBERS,
            ADMIN_ROLES,
            ADMIN_BILLING,
            ADMIN_INTEGRATIONS,
            ADMIN_SETTINGS,
            ADMIN_AUDIT,
            GROWTH_VIEW,
            GROWTH_ANALYZE,
            GROWTH_SIMULATE,
            RETENTION_VIEW,
            RETENTION_ANALYZE,
            RETENTION_SIMULATE,
            EXECUTIVE_VIEW,
            EXECUTIVE_TARGETS,
            EXECUTIVE_APPROVE,
            EXECUTIVE_SIMULATE,
            FINANCE_VIEW,
            FINANCE_EDIT_COSTS,
            FINANCE_ANALYZE,
            # Intelligence - all permissions
            INTEL_RECOMMENDATIONS_VIEW,
            INTEL_RECOMMENDATIONS_REVIEW,
            INTEL_RECOMMENDATIONS_APPROVE,
            INTEL_SIMULATIONS_RUN,
            INTEL_SIMULATIONS_VIEW,
            INTEL_INSIGHTS_VIEW,
            INTEL_ALERTS_MANAGE,
        ],
    }
    
    return role_permissions.get(role_name, [])

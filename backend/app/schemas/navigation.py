"""E8: Navigation menu schemas.

Persona-specific navigation menu structure based on role, permissions,
and feature flags.
"""

from pydantic import BaseModel, ConfigDict, Field


class NavigationMenuItem(BaseModel):
    """Single menu item in the navigation structure.

    E8: Each menu item includes path, label, icon, enabled status, and
    optional badge count (e.g., unread alerts, pending recommendations).
    """

    section: str = Field(
        description="Menu section grouping (e.g., 'intelligence', 'admin')"
    )
    label: str = Field(
        description="Display label for the menu item (e.g., 'Dashboard', 'Alerts')"
    )
    path: str = Field(
        description="Frontend route path (e.g., '/dashboard', '/recommendations')"
    )
    icon: str = Field(
        description="Icon identifier for frontend rendering (e.g., 'home', 'bell')"
    )
    enabled: bool = Field(
        description="Whether this menu item is enabled for the current user"
    )
    badge_count: int | None = Field(
        default=None,
        description="Optional badge count (e.g., 10 unread alerts)",
    )
    order: int = Field(
        description="Display order within section (lower = higher priority)"
    )

    model_config = ConfigDict(from_attributes=True)


class NavigationMenuResponse(BaseModel):
    """Complete navigation menu structure for a user.

    E8: Returns all menu items grouped by section, filtered by role,
    permissions, and feature flags. Frontend can render this directly
    without additional permission checks.
    """

    user_role: str = Field(
        description="User's role in the tenant (e.g., 'executive_owner')"
    )
    tenant_id: str = Field(
        description="Tenant identifier"
    )
    menu_items: list[NavigationMenuItem] = Field(
        description="All available menu items for this user"
    )

    model_config = ConfigDict(from_attributes=True)

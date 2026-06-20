"""
Pytest configuration and fixtures for all backend tests.
"""

import os
from collections.abc import Generator
from pathlib import Path
from uuid import UUID, uuid4

import jwt
import pytest
from backend.app.db.base import Base
from backend.app.db.models import Role, Tenant, TenantMembership, User
from backend.app.db.session import get_db
from backend.app.main import app
from backend.app.permissions import get_system_role_permissions
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Load .env file for tests if it exists (without external dependency)
_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    with open(_env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()


@pytest.fixture(scope="function")
def db_session() -> Generator[Session]:
    """Provide in-memory SQLite session for tests."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session, user: User) -> Generator[TestClient]:
    """Provide FastAPI test client with in-memory database and JWT auth."""
    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    # Generate valid JWT token for authenticated requests
    token = jwt.encode(
        {
            "sub": "test-user",
            "email": user.email,
            "platform_role": "super_admin",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )
    client.headers.update({"Authorization": f"Bearer {token}"})

    yield client
    app.dependency_overrides.clear()


def seed_system_roles_for_tenant(db: Session, tenant_id: UUID) -> dict[str, Role]:
    """
    Seed all 6 system roles for a tenant (mimics migration 0058 logic).
    Returns a dict mapping role names to Role objects.
    
    PUBLIC HELPER - Import this in test files that create tenants via API endpoints.
    """
    system_role_names = [
        "brand_admin",
        "executive_owner",
        "growth_performance_manager",
        "retention_crm_manager",
        "finance_controller",
        "operations_inventory_manager",
    ]
    
    roles_map = {}
    for role_name in system_role_names:
        permissions = get_system_role_permissions(role_name)
        role = Role(
            id=uuid4(),
            tenant_id=tenant_id,
            name=role_name,
            permissions=permissions,
            is_system=True,
        )
        db.add(role)
        roles_map[role_name] = role
    
    db.commit()
    return roles_map


@pytest.fixture
def tenant(db_session: Session) -> Tenant:
    """Create a test tenant with seeded system roles."""
    from backend.app.db.models import FeatureFlag
    from sqlalchemy import select

    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
    )
    db_session.add(tenant)
    db_session.commit()
    
    # Seed system roles (mimics migration 0058)
    seed_system_roles_for_tenant(db_session, tenant.id)
    
    # Enable feature flags by default for testing (if they don't exist)
    # Check if simulations flag exists
    simulations_exists = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "simulations")
    )
    if not simulations_exists:
        simulations_flag = FeatureFlag(
            slug="simulations",
            name="Simulations",
            description="Simulation engine",
            category="analytics",
            is_available=True,
            default_enabled=True,
        )
        db_session.add(simulations_flag)
    
    # Check if custom_segments flag exists
    custom_segments_exists = db_session.scalar(
        select(FeatureFlag).where(FeatureFlag.slug == "custom_segments")
    )
    if not custom_segments_exists:
        custom_segments_flag = FeatureFlag(
            slug="custom_segments",
            name="Custom Segments",
            description="Custom customer segments",
            category="analytics",
            is_available=True,
            default_enabled=True,
        )
        db_session.add(custom_segments_flag)
    
    db_session.commit()
    
    return tenant


@pytest.fixture
def other_tenant(db_session: Session) -> Tenant:
    """Create a second test tenant for isolation testing with seeded roles."""
    tenant = Tenant(
        id=uuid4(),
        name="Other Tenant",
        slug="other-tenant",
    )
    db_session.add(tenant)
    db_session.commit()
    
    # Seed system roles
    seed_system_roles_for_tenant(db_session, tenant.id)
    
    return tenant


@pytest.fixture
def user(db_session: Session, tenant: Tenant) -> User:
    """Create a test user with operations_inventory_manager role.
    
    This role has all permissions via system role for comprehensive testing.
    """
    from sqlalchemy import select
    
    user = User(
        id=uuid4(),
        email="testuser@example.com",
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Get the operations_inventory_manager system role for this tenant
    role = db_session.scalar(
        select(Role).where(
            Role.tenant_id == tenant.id,
            Role.name == "operations_inventory_manager",
            Role.is_system == True,  # noqa: E712
        )
    )
    assert role is not None, "operations_inventory_manager role must exist"
    
    # Add user to tenant with role_id
    membership = TenantMembership(
        id=uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="operations_inventory_manager",  # Keep string for legacy compat
        role_id=role.id,  # FK to actual role with permissions
    )
    db_session.add(membership)
    db_session.commit()
    return user


@pytest.fixture
def other_user(db_session: Session, tenant: Tenant) -> User:
    """Create a second test user with operations_inventory_manager role."""
    from sqlalchemy import select
    
    user = User(
        id=uuid4(),
        email="otheruser@example.com",
        full_name="Other User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Get the operations_inventory_manager system role for this tenant
    role = db_session.scalar(
        select(Role).where(
            Role.tenant_id == tenant.id,
            Role.name == "operations_inventory_manager",
            Role.is_system == True,  # noqa: E712
        )
    )
    assert role is not None, "operations_inventory_manager role must exist"
    
    # Add user to tenant with role_id
    membership = TenantMembership(
        id=uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="operations_inventory_manager",
        role_id=role.id,
    )
    db_session.add(membership)
    db_session.commit()
    return user


@pytest.fixture
def nonexistent_uuid() -> UUID:
    """Provide a UUID that does not exist in database."""
    return uuid4()


@pytest.fixture
def other_client(db_session: Session, other_user: User) -> Generator[TestClient]:
    """Provide TestClient authenticated as second user."""
    def override_get_db() -> Generator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    token = jwt.encode(
        {
            "sub": "other-user",
            "email": other_user.email,
            "platform_role": "user",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )
    client.headers.update({"Authorization": f"Bearer {token}"})

    yield client
    app.dependency_overrides.clear()


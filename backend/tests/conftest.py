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
from backend.app.db.models import Tenant, TenantMembership, User
from backend.app.db.session import get_db
from backend.app.main import app
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
            "platform_role": "user",
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )
    client.headers.update({"Authorization": f"Bearer {token}"})

    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def tenant(db_session: Session) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        id=uuid4(),
        name="Test Tenant",
        slug="test-tenant",
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def other_tenant(db_session: Session) -> Tenant:
    """Create a second test tenant for isolation testing."""
    tenant = Tenant(
        id=uuid4(),
        name="Other Tenant",
        slug="other-tenant",
    )
    db_session.add(tenant)
    db_session.commit()
    return tenant


@pytest.fixture
def user(db_session: Session, tenant: Tenant) -> User:
    """Create a test user."""
    user = User(
        id=uuid4(),
        email="testuser@example.com",
        full_name="Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Add user to tenant
    membership = TenantMembership(
        id=uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="operations_manager",
    )
    db_session.add(membership)
    db_session.commit()
    return user


@pytest.fixture
def other_user(db_session: Session, tenant: Tenant) -> User:
    """Create a second test user."""
    user = User(
        id=uuid4(),
        email="otheruser@example.com",
        full_name="Other User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()

    # Add user to tenant
    membership = TenantMembership(
        id=uuid4(),
        tenant_id=tenant.id,
        user_id=user.id,
        role="operations_manager",
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


"""Tests for authentication endpoints."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from backend.app.db.models import PasswordResetToken, User
from backend.app.password import hash_password, verify_password
from backend.app.security import AUTH_JWT_ALGORITHM, AUTH_JWT_SECRET
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def test_login_with_valid_credentials_returns_token(
    db_session: Session, client: TestClient
) -> None:
    """Test login with correct email and password returns JWT token."""
    # Create user with password
    user = User(
        email="admin@alpmark.com",
        full_name="Admin User",
        password_hash=hash_password("secretpass123"),
        is_active=True,
        is_platform_admin=True,
    )
    db_session.add(user)
    db_session.commit()

    # Remove auth header to test login endpoint
    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    # Login with correct credentials
    response = client.post(
        "/auth/login",
        json={"email": "admin@alpmark.com", "password": "secretpass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body

    # Verify JWT token is valid
    token = body["access_token"]
    payload = jwt.decode(token, AUTH_JWT_SECRET, algorithms=[AUTH_JWT_ALGORITHM])
    assert payload["email"] == "admin@alpmark.com"
    assert payload["sub"] == "admin@alpmark.com"
    assert payload["platform_role"] == "super_admin"
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload


def test_login_with_wrong_password_returns_401(
    db_session: Session, client: TestClient
) -> None:
    """Test login with wrong password returns 401."""
    user = User(
        email="user@alpmark.com",
        full_name="Regular User",
        password_hash=hash_password("correctpass"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/login",
        json={"email": "user@alpmark.com", "password": "wrongpass"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_with_nonexistent_email_returns_401(client: TestClient) -> None:
    """Test login with email that doesn't exist returns 401."""
    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "anypass"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_with_inactive_account_returns_401(
    db_session: Session, client: TestClient
) -> None:
    """Test login with inactive account returns 401."""
    user = User(
        email="inactive@alpmark.com",
        full_name="Inactive User",
        password_hash=hash_password("testpass"),
        is_active=False,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/login",
        json={"email": "inactive@alpmark.com", "password": "testpass"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Account is not active. Please contact support."


def test_login_with_no_password_hash_returns_401(
    db_session: Session, client: TestClient
) -> None:
    """Test login for user without password_hash returns 401."""
    user = User(
        email="nopass@alpmark.com",
        full_name="No Password User",
        password_hash=None,
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/login",
        json={"email": "nopass@alpmark.com", "password": "anypass"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_for_non_admin_user_returns_token_without_platform_role(
    db_session: Session, client: TestClient
) -> None:
    """Test that non-admin users get token with platform_role=None."""
    user = User(
        email="member@alpmark.com",
        full_name="Member User",
        password_hash=hash_password("memberpass"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/login",
        json={"email": "member@alpmark.com", "password": "memberpass"},
    )

    assert response.status_code == 200
    token = response.json()["access_token"]
    payload = jwt.decode(token, AUTH_JWT_SECRET, algorithms=[AUTH_JWT_ALGORITHM])
    assert payload["platform_role"] is None


def test_forgot_password_creates_reset_token(
    db_session: Session, client: TestClient
) -> None:
    """Test forgot password endpoint creates reset token."""
    user = User(
        email="reset@alpmark.com",
        full_name="Reset User",
        password_hash=hash_password("oldpass"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/forgot-password",
        json={"email": "reset@alpmark.com"},
    )

    assert response.status_code == 200
    assert "password reset link has been sent" in response.json()["message"]

    # Verify token was created
    reset_token = db_session.query(PasswordResetToken).filter_by(
        email="reset@alpmark.com"
    ).first()
    assert reset_token is not None
    assert reset_token.used_at is None
    
    # Handle both timezone-aware and naive datetimes
    now = datetime.now(UTC)
    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    assert expires_at > now


def test_forgot_password_nonexistent_email_returns_success(
    client: TestClient,
) -> None:
    """Test forgot password doesn't reveal if email exists (prevent enumeration)."""
    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )

    # Should return 200 even for non-existent email to prevent enumeration
    assert response.status_code == 200
    assert "password reset link has been sent" in response.json()["message"]


def test_reset_password_with_valid_token_updates_password(
    db_session: Session, client: TestClient
) -> None:
    """Test resetting password with valid token."""
    user = User(
        email="resetme@alpmark.com",
        full_name="Reset Me",
        password_hash=hash_password("oldpassword"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    # Create reset token
    reset_token = PasswordResetToken(
        email="resetme@alpmark.com",
        token="valid-reset-token-123",
    )
    db_session.add(reset_token)
    db_session.commit()

    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    # Reset password
    response = client.post(
        "/auth/reset-password",
        json={"token": "valid-reset-token-123", "new_password": "newpassword123"},
    )

    assert response.status_code == 200
    assert "successfully reset" in response.json()["message"]

    # Verify token is marked as used
    db_session.refresh(reset_token)
    assert reset_token.used_at is not None

    # Verify password was changed by attempting login
    login_response = client.post(
        "/auth/login",
        json={"email": "resetme@alpmark.com", "password": "newpassword123"},
    )
    assert login_response.status_code == 200


def test_reset_password_with_invalid_token_returns_404(
    client: TestClient,
) -> None:
    """Test reset password with non-existent token."""
    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/reset-password",
        json={"token": "invalid-token", "new_password": "newpass123"},
    )

    assert response.status_code == 404
    assert "Invalid or expired" in response.json()["detail"]


def test_reset_password_with_used_token_returns_409(
    db_session: Session, client: TestClient
) -> None:
    """Test reset password with already-used token."""
    user = User(
        email="alreadyreset@alpmark.com",
        full_name="Already Reset",
        password_hash=hash_password("password"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    # Create used reset token
    reset_token = PasswordResetToken(
        email="alreadyreset@alpmark.com",
        token="used-token-123",
        used_at=datetime.now(UTC),
    )
    db_session.add(reset_token)
    db_session.commit()

    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/reset-password",
        json={"token": "used-token-123", "new_password": "newpass123"},
    )

    assert response.status_code == 409
    assert "already been used" in response.json()["detail"]


def test_reset_password_with_expired_token_returns_410(
    db_session: Session, client: TestClient
) -> None:
    """Test reset password with expired token."""
    user = User(
        email="expired@alpmark.com",
        full_name="Expired User",
        password_hash=hash_password("password"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    # Create expired reset token (expired 1 hour ago)
    reset_token = PasswordResetToken(
        email="expired@alpmark.com",
        token="expired-token-123",
        expires_at=datetime.now(UTC) - timedelta(hours=1),
    )
    db_session.add(reset_token)
    db_session.commit()

    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/reset-password",
        json={"token": "expired-token-123", "new_password": "newpass123"},
    )

    assert response.status_code == 410
    assert "expired" in response.json()["detail"]


# Session Management Tests


def test_login_creates_user_session(
    db_session: Session, client: TestClient
) -> None:
    """Test that login creates a UserSession record."""
    from backend.app.db.models import UserSession
    
    user = User(
        email="session@alpmark.com",
        full_name="Session User",
        password_hash=hash_password("password123"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    if "Authorization" in client.headers:
        del client.headers["Authorization"]

    response = client.post(
        "/auth/login",
        json={"email": "session@alpmark.com", "password": "password123"},
    )

    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data

    # Verify session was created
    session = db_session.query(UserSession).filter_by(
        user_id=user.id
    ).first()
    assert session is not None
    assert session.revoked_at is None
    assert session.jti is not None


def test_get_user_sessions_returns_active_sessions(
    db_session: Session, client: TestClient
) -> None:
    """Test GET /me/sessions returns all active sessions for user."""
    from backend.app.db.models import UserSession
    
    user = User(
        email="sessions@alpmark.com",
        full_name="Sessions User",
        password_hash=hash_password("password123"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    # Create multiple sessions
    session1 = UserSession(
        user_id=user.id,
        jti=str(uuid.uuid4()),
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    session2 = UserSession(
        user_id=user.id,
        jti=str(uuid.uuid4()),
        ip_address="192.168.1.2",
        user_agent="Chrome/90.0",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    # Create a revoked session that should not appear
    session3 = UserSession(
        user_id=user.id,
        jti=str(uuid.uuid4()),
        ip_address="192.168.1.3",
        user_agent="Safari/14.0",
        expires_at=datetime.now(UTC) + timedelta(days=30),
        revoked_at=datetime.now(UTC),
    )
    db_session.add_all([session1, session2, session3])
    db_session.commit()

    # Create token with session1's jti
    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": None,
            "jti": session1.jti,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=24),
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    client.headers["Authorization"] = f"Bearer {token}"

    response = client.get("/me/sessions")

    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    # Should only show non-revoked sessions
    assert len(data["sessions"]) == 2
    
    # Check that current session is marked
    current_sessions = [s for s in data["sessions"] if s["is_current"]]
    assert len(current_sessions) == 1
    assert current_sessions[0]["jti"] == session1.jti


def test_logout_revokes_current_session(
    db_session: Session, client: TestClient
) -> None:
    """Test POST /auth/logout revokes the current session."""
    from backend.app.db.models import UserSession
    
    user = User(
        email="logout@alpmark.com",
        full_name="Logout User",
        password_hash=hash_password("password123"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    session = UserSession(
        user_id=user.id,
        jti=str(uuid.uuid4()),
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add(session)
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": None,
            "jti": session.jti,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=24),
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    client.headers["Authorization"] = f"Bearer {token}"

    response = client.post("/auth/logout")

    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()

    # Verify session was revoked
    db_session.refresh(session)
    assert session.revoked_at is not None


def test_logout_all_revokes_all_sessions(
    db_session: Session, client: TestClient
) -> None:
    """Test POST /auth/logout-all revokes all active sessions."""
    from backend.app.db.models import UserSession
    
    user = User(
        email="logoutall@alpmark.com",
        full_name="Logout All User",
        password_hash=hash_password("password123"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    # Create multiple sessions
    session1 = UserSession(
        user_id=user.id,
        jti=str(uuid.uuid4()),
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    session2 = UserSession(
        user_id=user.id,
        jti=str(uuid.uuid4()),
        ip_address="192.168.1.2",
        user_agent="Chrome/90.0",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db_session.add_all([session1, session2])
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": None,
            "jti": session1.jti,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=24),
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    client.headers["Authorization"] = f"Bearer {token}"

    response = client.post("/auth/logout-all")

    assert response.status_code == 200
    assert "2 session" in response.json()["message"]

    # Verify both sessions were revoked
    db_session.refresh(session1)
    db_session.refresh(session2)
    assert session1.revoked_at is not None
    assert session2.revoked_at is not None


def test_revoked_session_cannot_access_endpoints(
    db_session: Session, client: TestClient
) -> None:
    """Test that a revoked session cannot access protected endpoints."""
    from backend.app.db.models import UserSession
    
    user = User(
        email="revoked@alpmark.com",
        full_name="Revoked User",
        password_hash=hash_password("password123"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    session = UserSession(
        user_id=user.id,
        jti=str(uuid.uuid4()),
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        expires_at=datetime.now(UTC) + timedelta(days=30),
        revoked_at=datetime.now(UTC),  # Already revoked
    )
    db_session.add(session)
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": None,
            "jti": session.jti,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=24),
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    client.headers["Authorization"] = f"Bearer {token}"

    response = client.get("/me/sessions")

    assert response.status_code == 401
    assert "revoked" in response.json()["detail"].lower()


def test_change_password_with_valid_credentials_succeeds(
    db_session: Session, client: TestClient
) -> None:
    """Test that a user can change their password with correct current password."""
    user = User(
        email="changepass@alpmark.com",
        full_name="Change Password User",
        password_hash=hash_password("oldpassword123"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": None,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=24),
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    client.headers["Authorization"] = f"Bearer {token}"

    response = client.patch(
        "/users/me/password",
        json={
            "current_password": "oldpassword123",
            "new_password": "newpassword456",
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password updated successfully"

    # Verify password was actually changed in database
    db_session.refresh(user)
    assert user.password_hash is not None
    assert verify_password("newpassword456", user.password_hash)
    assert not verify_password("oldpassword123", user.password_hash)


def test_change_password_with_incorrect_current_password_fails(
    db_session: Session, client: TestClient
) -> None:
    """Test that password change fails if current password is incorrect."""
    user = User(
        email="wrongpass@alpmark.com",
        full_name="Wrong Password User",
        password_hash=hash_password("correctpassword"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": None,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=24),
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    client.headers["Authorization"] = f"Bearer {token}"

    response = client.patch(
        "/users/me/password",
        json={
            "current_password": "wrongpassword",
            "new_password": "newpassword456",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Current password is incorrect"

    # Verify password was not changed
    db_session.refresh(user)
    assert user.password_hash is not None
    assert verify_password("correctpassword", user.password_hash)


def test_change_password_with_short_new_password_fails(
    db_session: Session, client: TestClient
) -> None:
    """Test that password change fails if new password is too short."""
    user = User(
        email="shortpass@alpmark.com",
        full_name="Short Password User",
        password_hash=hash_password("oldpassword123"),
        is_active=True,
        is_platform_admin=False,
    )
    db_session.add(user)
    db_session.commit()

    token = jwt.encode(
        {
            "sub": user.email,
            "email": user.email,
            "platform_role": None,
            "iat": datetime.now(UTC),
            "exp": datetime.now(UTC) + timedelta(hours=24),
        },
        AUTH_JWT_SECRET,
        algorithm=AUTH_JWT_ALGORITHM,
    )

    client.headers["Authorization"] = f"Bearer {token}"

    response = client.patch(
        "/users/me/password",
        json={
            "current_password": "oldpassword123",
            "new_password": "short",
        },
    )

    assert response.status_code == 422  # Validation error
    assert "new_password" in str(response.json())

    # Verify password was not changed
    db_session.refresh(user)
    assert user.password_hash is not None
    assert verify_password("oldpassword123", user.password_hash)


def test_change_password_without_authentication_fails(client: TestClient) -> None:
    """Test that password change fails without authentication token."""
    response = client.patch(
        "/users/me/password",
        json={
            "current_password": "oldpassword123",
            "new_password": "newpassword456",
        },
    )

    # FastAPI returns 400 when auth is missing because the endpoint requires AuthDep
    assert response.status_code in [400, 401]


"""Test dummy AccountMatrix module."""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from src.dbm.connection import DummyDBConnection
from src.accountmatrix.auth import DummyAuth
from src.accountmatrix.session import DummySessionManager


@pytest.fixture
def temp_db_path():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def test_auth(temp_db_path):
    """Create a test authentication instance."""
    # Override the global connection for testing
    from src.dbm import connection, operations
    original_connection = connection._db_connection
    original_operations = operations._db_operations
    
    # Create test connection
    test_connection = DummyDBConnection(temp_db_path)
    connection._db_connection = test_connection
    operations._db_operations = None  # Reset to create new instance
    
    auth = DummyAuth()
    yield auth
    
    # Restore original instances
    connection._db_connection = original_connection
    operations._db_operations = original_operations


@pytest.fixture
def test_session_manager(temp_db_path):
    """Create a test session manager instance."""
    # Override the global connection for testing
    from src.dbm import connection, operations
    original_connection = connection._db_connection
    original_operations = operations._db_operations
    
    # Create test connection
    test_connection = DummyDBConnection(temp_db_path)
    connection._db_connection = test_connection
    operations._db_operations = None  # Reset to create new instance
    
    session_manager = DummySessionManager(session_timeout_hours=1)
    yield session_manager
    
    # Restore original instances
    connection._db_connection = original_connection
    operations._db_operations = original_operations


def test_auth_default_user_creation(test_auth):
    """Test that default admin user is created."""
    user = test_auth.authenticate_user("admin", "admin123")
    assert user is not None
    assert user["username"] == "admin"
    assert user["email"] == "admin@brain-mvp.com"
    assert "admin" in user["roles"]
    assert "password_hash" not in user  # Should not return password hash


def test_auth_password_hashing(test_auth):
    """Test password hashing functionality."""
    password = "test_password"
    hash1 = test_auth._hash_password(password)
    hash2 = test_auth._hash_password(password)
    
    # Same password should produce same hash (with fixed salt)
    assert hash1 == hash2
    
    # Different passwords should produce different hashes
    different_hash = test_auth._hash_password("different_password")
    assert hash1 != different_hash


def test_auth_password_verification(test_auth):
    """Test password verification."""
    password = "test_password"
    password_hash = test_auth._hash_password(password)
    
    # Correct password should verify
    assert test_auth._verify_password(password, password_hash) is True
    
    # Incorrect password should not verify
    assert test_auth._verify_password("wrong_password", password_hash) is False


def test_auth_user_creation(test_auth):
    """Test user creation."""
    user_id = test_auth.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",
        roles=["user"],
        permissions=["read", "write"]
    )
    
    assert user_id is not None
    assert user_id.startswith("user-")
    
    # Test authentication with new user
    user = test_auth.authenticate_user("testuser", "testpass123")
    assert user is not None
    assert user["username"] == "testuser"
    assert user["email"] == "test@example.com"


def test_auth_duplicate_user_creation(test_auth):
    """Test that duplicate users cannot be created."""
    # Create first user
    user_id1 = test_auth.create_user(
        username="duplicate_test",
        email="duplicate@example.com",
        password="password123"
    )
    assert user_id1 is not None
    
    # Try to create duplicate username
    user_id2 = test_auth.create_user(
        username="duplicate_test",
        email="different@example.com",
        password="password456"
    )
    assert user_id2 is None
    
    # Try to create duplicate email
    user_id3 = test_auth.create_user(
        username="different_user",
        email="duplicate@example.com",
        password="password789"
    )
    assert user_id3 is None


def test_auth_invalid_authentication(test_auth):
    """Test authentication with invalid credentials."""
    # Non-existent user
    user = test_auth.authenticate_user("nonexistent", "password")
    assert user is None
    
    # Wrong password for existing user
    user = test_auth.authenticate_user("admin", "wrong_password")
    assert user is None


def test_auth_get_user(test_auth):
    """Test getting user by ID."""
    # Create a test user
    user_id = test_auth.create_user(
        username="getuser_test",
        email="getuser@example.com",
        password="password123"
    )
    
    # Get user by ID
    user = test_auth.get_user(user_id)
    assert user is not None
    assert user["user_id"] == user_id
    assert user["username"] == "getuser_test"
    assert "password_hash" not in user
    
    # Test with non-existent user ID
    non_existent_user = test_auth.get_user("non-existent-id")
    assert non_existent_user is None


def test_session_creation(test_session_manager):
    """Test session creation."""
    user_id = "test-user-123"
    session_token = test_session_manager.create_session(user_id)
    
    assert session_token is not None
    assert len(session_token) > 20  # Should be a reasonable length token


def test_session_validation(test_session_manager):
    """Test session validation."""
    user_id = "test-user-456"
    session_token = test_session_manager.create_session(user_id)
    
    # Valid session should return user_id
    validated_user_id = test_session_manager.validate_session(session_token)
    assert validated_user_id == user_id
    
    # Invalid session should return None
    invalid_result = test_session_manager.validate_session("invalid-token")
    assert invalid_result is None


def test_session_invalidation(test_session_manager):
    """Test session invalidation."""
    user_id = "test-user-789"
    session_token = test_session_manager.create_session(user_id)
    
    # Session should be valid initially
    assert test_session_manager.validate_session(session_token) == user_id
    
    # Invalidate session
    result = test_session_manager.invalidate_session(session_token)
    assert result is True
    
    # Session should no longer be valid
    assert test_session_manager.validate_session(session_token) is None


def test_session_refresh(test_session_manager):
    """Test session refresh."""
    user_id = "test-user-refresh"
    session_token = test_session_manager.create_session(user_id)
    
    # Refresh session
    result = test_session_manager.refresh_session(session_token)
    assert result is True
    
    # Session should still be valid
    assert test_session_manager.validate_session(session_token) == user_id


def test_session_user_sessions(test_session_manager):
    """Test getting user sessions."""
    user_id = "test-user-sessions"
    
    # Create multiple sessions for the same user
    token1 = test_session_manager.create_session(user_id)
    token2 = test_session_manager.create_session(user_id)
    
    # Get user sessions
    sessions = test_session_manager.get_user_sessions(user_id)
    assert len(sessions) >= 2
    
    # All sessions should belong to the same user
    for session in sessions:
        assert session["user_id"] == user_id
        assert session["is_active"] == 1  # SQLite returns 1 for TRUE


def test_session_cleanup(test_session_manager):
    """Test expired session cleanup."""
    # This test is limited since we can't easily create expired sessions
    # in the test environment, but we can test that the method runs
    cleaned_count = test_session_manager.cleanup_expired_sessions()
    assert isinstance(cleaned_count, int)
    assert cleaned_count >= 0


def test_integrated_auth_and_session(test_auth, test_session_manager):
    """Test integrated authentication and session management."""
    # Create user
    user_id = test_auth.create_user(
        username="integrated_test",
        email="integrated@example.com",
        password="password123"
    )
    
    # Authenticate user
    user = test_auth.authenticate_user("integrated_test", "password123")
    assert user is not None
    
    # Create session
    session_token = test_session_manager.create_session(user["user_id"])
    assert session_token is not None
    
    # Validate session
    validated_user_id = test_session_manager.validate_session(session_token)
    assert validated_user_id == user["user_id"]
    
    # Get user info using session
    user_info = test_auth.get_user(validated_user_id)
    assert user_info["username"] == "integrated_test"
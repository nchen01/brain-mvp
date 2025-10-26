"""Basic authentication for dummy AccountMatrix."""

import hashlib
import secrets
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from dbm.operations import get_db_operations

logger = logging.getLogger(__name__)


class DummyAuth:
    """Dummy authentication system for MVP."""
    
    def __init__(self):
        self.db = get_db_operations()
        self._create_default_user()
    
    def _create_default_user(self) -> None:
        """Create a default user for testing."""
        try:
            # Check if default user exists
            existing_users = self.db.select(
                "users",
                "username = ?",
                ("admin",)
            )
            
            if not existing_users:
                # Create default admin user
                password_hash = self._hash_password("admin123")
                user_data = {
                    "user_id": "admin-001",
                    "username": "admin",
                    "email": "admin@brain-mvp.com",
                    "password_hash": password_hash,
                    "roles": ["admin", "user"],
                    "permissions": ["read", "write", "delete", "admin"],
                    "created_at": datetime.utcnow().isoformat()
                }
                
                self.db.insert("users", user_data)
                logger.info("Default admin user created")
                
        except Exception as e:
            logger.error(f"Failed to create default user: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash a password using SHA-256 (dummy implementation)."""
        # Note: In production, use proper password hashing like bcrypt
        salt = "brain_mvp_salt"  # Fixed salt for simplicity
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash."""
        return self._hash_password(password) == password_hash
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user with username and password."""
        try:
            users = self.db.select(
                "users",
                "username = ? AND is_active = TRUE",
                (username,)
            )
            
            if not users:
                logger.warning(f"Authentication failed: user not found - {username}")
                return None
            
            user = users[0]
            
            if not self._verify_password(password, user["password_hash"]):
                logger.warning(f"Authentication failed: invalid password - {username}")
                return None
            
            # Update last login
            self.db.update(
                "users",
                {"last_login": datetime.utcnow().isoformat()},
                "user_id = ?",
                (user["user_id"],)
            )
            
            # Remove password hash from returned user data
            user_data = dict(user)
            del user_data["password_hash"]
            
            logger.info(f"User authenticated successfully: {username}")
            return user_data
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: Optional[list] = None,
        permissions: Optional[list] = None
    ) -> Optional[str]:
        """Create a new user."""
        try:
            # Check if user already exists
            existing_users = self.db.select(
                "users",
                "username = ? OR email = ?",
                (username, email)
            )
            
            if existing_users:
                logger.warning(f"User creation failed: user already exists - {username}")
                return None
            
            user_id = f"user-{secrets.token_hex(8)}"
            password_hash = self._hash_password(password)
            
            user_data = {
                "user_id": user_id,
                "username": username,
                "email": email,
                "password_hash": password_hash,
                "roles": roles or ["user"],
                "permissions": permissions or ["read"],
                "created_at": datetime.utcnow().isoformat()
            }
            
            if self.db.insert("users", user_data):
                logger.info(f"User created successfully: {username}")
                return user_id
            else:
                return None
                
        except Exception as e:
            logger.error(f"User creation error: {e}")
            return None
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            users = self.db.select(
                "users",
                "user_id = ?",
                (user_id,)
            )
            
            if users:
                user_data = dict(users[0])
                del user_data["password_hash"]  # Don't return password hash
                return user_data
            
            return None
            
        except Exception as e:
            logger.error(f"Get user error: {e}")
            return None
    
    def update_user(
        self,
        user_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update user information."""
        try:
            # Don't allow updating sensitive fields directly
            allowed_fields = ["email", "roles", "permissions"]
            filtered_updates = {
                k: v for k, v in updates.items()
                if k in allowed_fields
            }
            
            if not filtered_updates:
                return False
            
            return self.db.update(
                "users",
                filtered_updates,
                "user_id = ?",
                (user_id,)
            )
            
        except Exception as e:
            logger.error(f"Update user error: {e}")
            return False
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password."""
        try:
            users = self.db.select(
                "users",
                "user_id = ?",
                (user_id,)
            )
            
            if not users:
                return False
            
            user = users[0]
            
            if not self._verify_password(old_password, user["password_hash"]):
                logger.warning(f"Password change failed: invalid old password - {user_id}")
                return False
            
            new_password_hash = self._hash_password(new_password)
            
            return self.db.update(
                "users",
                {"password_hash": new_password_hash},
                "user_id = ?",
                (user_id,)
            )
            
        except Exception as e:
            logger.error(f"Change password error: {e}")
            return False
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users (for testing/admin purposes)."""
        try:
            users = self.db.select("users", "1=1", ())
            
            # Remove password hashes from returned data
            user_list = []
            for user in users:
                user_data = dict(user)
                del user_data["password_hash"]  # Don't return password hash
                user_list.append(user_data)
            
            return user_list
            
        except Exception as e:
            logger.error(f"List users error: {e}")
            return []
    
    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        try:
            return self.db.update(
                "users",
                {"last_login": datetime.utcnow().isoformat()},
                "user_id = ?",
                (user_id,)
            )
        except Exception as e:
            logger.error(f"Update last login error: {e}")
            return False


# Global auth instance
_auth: Optional[DummyAuth] = None


def get_auth() -> DummyAuth:
    """Get global authentication instance."""
    global _auth
    if not _auth:
        _auth = DummyAuth()
    return _auth
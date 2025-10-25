"""Simple session management for dummy AccountMatrix."""

import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from dbm.operations import get_db_operations

logger = logging.getLogger(__name__)


class DummySessionManager:
    """Dummy session management system for MVP."""
    
    def __init__(self, session_timeout_hours: int = 24):
        self.db = get_db_operations()
        self.session_timeout_hours = session_timeout_hours
    
    def create_session(self, user_id: str) -> Optional[str]:
        """Create a new session for a user."""
        try:
            # Generate session token
            session_token = secrets.token_urlsafe(32)
            
            # Calculate expiration time
            expires_at = datetime.utcnow() + timedelta(hours=self.session_timeout_hours)
            
            session_data = {
                "session_token": session_token,
                "user_id": user_id,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at.isoformat(),
                "is_active": True
            }
            
            if self.db.insert("sessions", session_data):
                logger.info(f"Session created for user: {user_id}")
                return session_token
            else:
                return None
                
        except Exception as e:
            logger.error(f"Session creation error: {e}")
            return None
    
    def validate_session(self, session_token: str) -> Optional[str]:
        """Validate a session token and return user_id if valid."""
        try:
            sessions = self.db.select(
                "sessions",
                "session_token = ? AND is_active = TRUE",
                (session_token,)
            )
            
            if not sessions:
                logger.warning(f"Session validation failed: token not found")
                return None
            
            session = sessions[0]
            
            # Check if session has expired
            expires_at = datetime.fromisoformat(session["expires_at"])
            if datetime.utcnow() > expires_at:
                # Mark session as inactive
                self.db.update(
                    "sessions",
                    {"is_active": False},
                    "session_token = ?",
                    (session_token,)
                )
                logger.warning(f"Session validation failed: token expired")
                return None
            
            logger.info(f"Session validated for user: {session['user_id']}")
            return session["user_id"]
            
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    def refresh_session(self, session_token: str) -> bool:
        """Refresh a session by extending its expiration time."""
        try:
            user_id = self.validate_session(session_token)
            if not user_id:
                return False
            
            # Extend expiration time
            new_expires_at = datetime.utcnow() + timedelta(hours=self.session_timeout_hours)
            
            return self.db.update(
                "sessions",
                {"expires_at": new_expires_at.isoformat()},
                "session_token = ?",
                (session_token,)
            )
            
        except Exception as e:
            logger.error(f"Session refresh error: {e}")
            return False
    
    def invalidate_session(self, session_token: str) -> bool:
        """Invalidate a session (logout)."""
        try:
            return self.db.update(
                "sessions",
                {"is_active": False},
                "session_token = ?",
                (session_token,)
            )
            
        except Exception as e:
            logger.error(f"Session invalidation error: {e}")
            return False
    
    def invalidate_user_sessions(self, user_id: str) -> bool:
        """Invalidate all sessions for a user."""
        try:
            return self.db.update(
                "sessions",
                {"is_active": False},
                "user_id = ?",
                (user_id,)
            )
            
        except Exception as e:
            logger.error(f"User sessions invalidation error: {e}")
            return False
    
    def get_user_sessions(self, user_id: str, active_only: bool = True) -> list:
        """Get all sessions for a user."""
        try:
            where_clause = "user_id = ?"
            params = (user_id,)
            
            if active_only:
                where_clause += " AND is_active = TRUE"
            
            return self.db.select("sessions", where_clause, params)
            
        except Exception as e:
            logger.error(f"Get user sessions error: {e}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        try:
            # Mark expired sessions as inactive
            current_time = datetime.utcnow().isoformat()
            
            # First, get count of expired sessions
            expired_count = self.db.count(
                "sessions",
                "expires_at < ? AND is_active = TRUE",
                (current_time,)
            )
            
            # Mark them as inactive
            self.db.update(
                "sessions",
                {"is_active": False},
                "expires_at < ? AND is_active = TRUE",
                (current_time,)
            )
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired sessions")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")
            return 0
    
    def get_session_info(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        try:
            sessions = self.db.select(
                "sessions",
                "session_token = ?",
                (session_token,)
            )
            
            return sessions[0] if sessions else None
            
        except Exception as e:
            logger.error(f"Get session info error: {e}")
            return None


# Global session manager instance
_session_manager: Optional[DummySessionManager] = None


def get_session_manager() -> DummySessionManager:
    """Get global session manager instance."""
    global _session_manager
    if not _session_manager:
        _session_manager = DummySessionManager()
    return _session_manager
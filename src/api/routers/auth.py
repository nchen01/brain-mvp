"""Authentication API endpoints."""

import logging
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import jwt

# Import our authentication system
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))

from accountmatrix.auth import DummyAuth, get_auth
from accountmatrix.session import DummySessionManager
from config.config_manager import ConfigManager

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])

# Security scheme
security = HTTPBearer()

# JWT settings (in production, use proper secret management)
JWT_SECRET = "docforge-brain-mvp-secret-key"  # Should be in environment variables
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Pydantic models
class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field("bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration in seconds")
    user_info: dict = Field(..., description="User information")


class UserInfo(BaseModel):
    """User information model."""
    user_id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    roles: list = []
    permissions: list = []
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None


class TokenValidationResponse(BaseModel):
    """Token validation response."""
    valid: bool
    user_info: Optional[UserInfo] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


# Dependency injection
async def get_auth_manager() -> DummyAuth:
    """Get authentication manager instance."""
    return get_auth()


async def get_session_manager() -> DummySessionManager:
    """Get session manager instance.""" 
    return DummySessionManager()


def create_access_token(user_data: dict) -> str:
    """Create JWT access token."""
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode = {
        **user_data,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access_token"
    }
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_manager: DummyAuth = Depends(get_auth_manager)
) -> UserInfo:
    """Get current authenticated user."""
    try:
        # Verify JWT token
        payload = verify_token(credentials.credentials)
        
        # Get user info
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Validate user still exists and is active
        user = auth_manager.get_user(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return UserInfo(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            roles=user.roles,
            permissions=user.permissions,
            created_at=user.created_at,
            last_login=user.last_login
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


# Optional dependency for endpoints that can work with or without auth
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    auth_manager: DummyAuth = Depends(get_auth_manager)
) -> Optional[UserInfo]:
    """Get current user if authenticated, None otherwise."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, auth_manager)
    except HTTPException:
        return None


@router.post("/login", response_model=LoginResponse)
async def login(
    login_request: LoginRequest,
    auth_manager: DummyAuth = Depends(get_auth_manager),
    session_manager: DummySessionManager = Depends(get_session_manager)
):
    """
    Authenticate user and return access token.
    
    - **username**: User's username
    - **password**: User's password
    """
    try:
        # Authenticate user
        user = auth_manager.authenticate_user(
            login_request.username,
            login_request.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Create session
        session_id = session_manager.create_session(user["user_id"])
        
        # Create JWT token
        token_data = {
            "user_id": user["user_id"],
            "username": user["username"],
            "session_id": session_id
        }
        
        access_token = create_access_token(token_data)
        
        # Update last login (skip if database is readonly)
        try:
            auth_manager.update_last_login(user["user_id"])
        except Exception as e:
            logger.warning(f"Could not update last login: {e}")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_EXPIRATION_HOURS * 3600,
            user_info={
                "user_id": user["user_id"],
                "username": user["username"],
                "email": user.get("email", ""),
                "full_name": user.get("full_name", user["username"]),
                "roles": user.get("roles", []),
                "permissions": user.get("permissions", []),
                "permissions": user.permissions
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/logout")
async def logout(
    current_user: UserInfo = Depends(get_current_user),
    session_manager: DummySessionManager = Depends(get_session_manager)
):
    """
    Logout current user and invalidate session.
    """
    try:
        # Invalidate all sessions for user (simple approach)
        session_manager.invalidate_user_sessions(current_user.user_id)
        
        return {
            "message": "Logged out successfully",
            "user_id": current_user.user_id,
            "logged_out_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    return current_user


@router.post("/validate", response_model=TokenValidationResponse)
async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_manager: DummyAuth = Depends(get_auth_manager)
):
    """
    Validate JWT token and return user information.
    """
    try:
        # Verify token
        payload = verify_token(credentials.credentials)
        
        # Get user info
        user_id = payload.get("user_id")
        user = auth_manager.get_user(user_id) if user_id else None
        
        if not user:
            return TokenValidationResponse(
                valid=False,
                error_message="User not found"
            )
        
        return TokenValidationResponse(
            valid=True,
            user_info=UserInfo(
                user_id=user.user_id,
                username=user.username,
                email=user.email,
                full_name=user.full_name,
                roles=user.roles,
                permissions=user.permissions,
                created_at=user.created_at,
                last_login=user.last_login
            ),
            expires_at=datetime.fromtimestamp(payload.get("exp", 0))
        )
        
    except HTTPException as e:
        return TokenValidationResponse(
            valid=False,
            error_message=e.detail
        )
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return TokenValidationResponse(
            valid=False,
            error_message="Token validation failed"
        )


@router.get("/permissions")
async def get_user_permissions(
    current_user: UserInfo = Depends(get_current_user)
):
    """
    Get current user's permissions and roles.
    """
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "roles": current_user.roles,
        "permissions": current_user.permissions,
        "document_access": {
            "can_upload": "document:upload" in current_user.permissions,
            "can_delete": "document:delete" in current_user.permissions,
            "can_view_all": "document:view_all" in current_user.permissions,
            "can_manage_versions": "document:manage_versions" in current_user.permissions
        }
    }


# Test endpoints for development
@router.get("/test/users")
async def list_test_users(
    auth_manager: DummyAuth = Depends(get_auth_manager)
):
    """
    List available test users (development only).
    """
    try:
        users = auth_manager.list_users()
        return {
            "message": "Available test users",
            "users": [
                {
                    "username": user["username"],
                    "email": user["email"],
                    "roles": user["roles"],
                    "permissions": user["permissions"]
                }
                for user in users
            ],
            "note": "Use these credentials for testing the API"
        }
        
    except Exception as e:
        logger.error(f"Error listing test users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list test users"
        )
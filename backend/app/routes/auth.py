"""
Authentication routes for user registration, login, and token management.
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from app.schemas import UserCreate, UserLogin, UserResponse, TokenResponse
from app.models import User
from app.crud import create_user, get_user_by_email
from app.auth import verify_password, create_tokens_for_user, verify_token
from app.dependencies import get_current_user, security, rate_limit_strict
from app.logger import get_logger
from app.exceptions import ValidationError, DatabaseError

logger = get_logger("auth_routes")
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, _: None = Depends(rate_limit_strict)):  # Rate limit: 50 requests per minute
    """Register a new user account."""
    try:
        logger.info(f"Registration attempt for email: {user_data.email}")
        
        # Create user
        user = create_user(user_data)
        
        # Generate tokens
        tokens = create_tokens_for_user(user.id, user.email)
        
        logger.info(f"User registered successfully: {user.email}")
        return tokens
        
    except ValidationError as e:
        logger.warning(f"Registration validation error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
    except DatabaseError as e:
        logger.error(f"Registration database error: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )
    except Exception as e:
        logger.error(f"Unexpected registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(user_credentials: UserLogin, _: None = Depends(rate_limit_strict)):  # Rate limit: 50 requests per minute
    """Authenticate user and return access tokens."""
    try:
        logger.info(f"Login attempt for email: {user_credentials.email}")
        
        # Get user by email
        user = get_user_by_email(user_credentials.email)
        if not user:
            logger.warning(f"Login failed - user not found: {user_credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login failed - inactive user: {user_credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive"
            )
        
        # Verify password
        if not verify_password(user_credentials.password, user.hashed_password):
            logger.warning(f"Login failed - invalid password: {user_credentials.email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Generate tokens
        tokens = create_tokens_for_user(user.id, user.email)
        
        logger.info(f"User logged in successfully: {user.email}")
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Refresh access token using refresh token."""
    try:
        # Verify refresh token
        payload = verify_token(credentials.credentials, token_type="refresh")
        
        user_id = payload.get("sub")
        email = payload.get("email")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Generate new tokens
        tokens = create_tokens_for_user(user_id, email)
        
        logger.info(f"Token refreshed for user: {email}")
        return tokens
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh token"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    try:
        # Convert User model to response format
        user_response = UserResponse(
            id=current_user.id,
            email=current_user.email,
            username=current_user.username,
            full_name=current_user.full_name,
            is_active=current_user.is_active,
            is_verified=current_user.is_verified,
            profile_image_url=current_user.profile_image_url,
            bio=current_user.bio,
            created_at=current_user.created_at,
            upload_count=0  # You can implement this later
        )
        
        return user_response
        
    except Exception as e:
        logger.error(f"Error getting current user info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not retrieve user information"
        )

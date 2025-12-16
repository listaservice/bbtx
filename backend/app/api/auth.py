"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, LoginResponse
from app.schemas.user import UserResponse
from app.services.auth_service import auth_service
from app.services.google_sheets_multi import google_sheets_multi_service
from app.dependencies import get_current_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user

    - **email**: Valid email address
    - **password**: Minimum 8 characters
    - **full_name**: Optional full name

    Returns the created user object (without password)
    """
    try:
        # Create user
        user = auth_service.create_user(
            db=db,
            email=request.email,
            password=request.password,
            full_name=request.full_name
        )

        # Create Google Sheets spreadsheet for user
        try:
            spreadsheet_id = google_sheets_multi_service.create_user_spreadsheet(
                user_email=user.email,
                user_id=user.id
            )
            if spreadsheet_id:
                user.google_sheets_id = spreadsheet_id
                db.commit()
                logger.info(f"Created Google Sheets for user {user.email}: {spreadsheet_id}")
        except Exception as sheets_error:
            logger.warning(f"Could not create Google Sheets for {user.email}: {sheets_error}")
            # Nu aruncăm eroare - user-ul e creat, doar sheets nu a mers

        return user

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login with email and password

    - **email**: User email
    - **password**: User password

    Returns JWT access token and user info
    """
    # Authenticate user
    user = auth_service.authenticate_user(
        db=db,
        email=request.email,
        password=request.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Create access token
    access_token = auth_service.create_access_token(
        data={"sub": user.id}
    )

    # Update last login
    auth_service.update_last_login(db=db, user_id=user.id)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        email=user.email,
        subscription_plan=user.subscription_plan,
        subscription_status=user.subscription_status,
        max_teams=user.max_teams,
        trial_ends_at=user.trial_ends_at.isoformat() if user.trial_ends_at else None,
        subscription_ends_at=user.subscription_ends_at.isoformat() if user.subscription_ends_at else None
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user info

    Requires valid JWT token in Authorization header:
    ```
    Authorization: Bearer <token>
    ```

    Returns current user object
    """
    return current_user


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """
    Logout current user

    Note: JWT tokens are stateless, so logout is handled client-side
    by removing the token. This endpoint is just for consistency.
    """
    return {
        "message": "Logged out successfully",
        "user_id": current_user.id
    }

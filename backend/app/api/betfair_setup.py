"""
Betfair Setup API endpoints
Handles user Betfair credentials configuration
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from app.database import get_db
from app.models.user import User
from app.models.betfair_credentials import BetfairCredentials
from app.dependencies import get_current_user
from app.services.encryption import encryption_service
from app.services.betfair_client import BetfairClient

router = APIRouter(prefix="/betfair", tags=["betfair"])
logger = logging.getLogger(__name__)


class VerifyCredentialsRequest(BaseModel):
    username: str
    password: str


class SaveCredentialsRequest(BaseModel):
    username: str
    password: str
    app_key: str
    cert_content: Optional[str] = None
    key_content: Optional[str] = None


class CredentialsStatusResponse(BaseModel):
    is_configured: bool
    has_app_key: bool
    has_certificate: bool
    username: Optional[str] = None


@router.post("/verify-credentials")
async def verify_betfair_credentials(
    request: VerifyCredentialsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify Betfair credentials - simplified version

    Note: Full verification requires SSL certificate.
    We accept credentials here and verify when bot runs.

    Returns:
        success: bool
        message: str
    """
    try:
        # Basic validation
        if not request.username or not request.password:
            return {
                "success": False,
                "message": "Username și parola sunt obligatorii"
            }

        if len(request.password) < 6:
            return {
                "success": False,
                "message": "Parola pare prea scurtă. Verifică că ai introdus parola corectă."
            }

        # Accept credentials (will be verified when bot runs with SSL cert)
        logger.info(f"Accepting Betfair credentials for user {current_user.email}")

        return {
            "success": True,
            "message": "Credențiale acceptate! ✅ Vor fi verificate când bot-ul rulează cu certificatul SSL."
        }

    except Exception as e:
        logger.error(f"Error verifying Betfair credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Eroare la verificarea credențialelor"
        )


@router.post("/save-credentials")
async def save_betfair_credentials(
    request: SaveCredentialsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save encrypted Betfair credentials for user

    Returns:
        success: bool
        message: str
    """
    try:
        # Check if credentials already exist
        existing = db.query(BetfairCredentials).filter(
            BetfairCredentials.user_id == current_user.id
        ).first()

        # Encrypt sensitive data
        encrypted_username = encryption_service.encrypt(request.username)
        encrypted_password = encryption_service.encrypt(request.password)
        encrypted_app_key = encryption_service.encrypt(request.app_key)

        encrypted_cert = None
        encrypted_key = None

        if request.cert_content:
            encrypted_cert = encryption_service.encrypt(request.cert_content)
        if request.key_content:
            encrypted_key = encryption_service.encrypt(request.key_content)

        if existing:
            # Update existing
            existing.username_encrypted = encrypted_username
            existing.password_encrypted = encrypted_password
            existing.app_key_encrypted = encrypted_app_key
            existing.cert_encrypted = encrypted_cert
            existing.key_encrypted = encrypted_key
            existing.is_configured = True

            logger.info(f"Updated Betfair credentials for user {current_user.email}")
        else:
            # Create new
            credentials = BetfairCredentials(
                user_id=current_user.id,
                username_encrypted=encrypted_username,
                password_encrypted=encrypted_password,
                app_key_encrypted=encrypted_app_key,
                cert_encrypted=encrypted_cert,
                key_encrypted=encrypted_key,
                is_configured=True
            )
            db.add(credentials)

            logger.info(f"Created Betfair credentials for user {current_user.email}")

        db.commit()

        return {
            "success": True,
            "message": "Credențiale Betfair salvate cu succes! 🎉"
        }

    except Exception as e:
        logger.error(f"Error saving Betfair credentials: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Eroare la salvarea credențialelor"
        )


@router.get("/credentials-status", response_model=CredentialsStatusResponse)
async def get_credentials_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's Betfair credentials configuration status

    Returns:
        is_configured: bool
        has_app_key: bool
        has_certificate: bool
        username: str (decrypted)
    """
    try:
        credentials = db.query(BetfairCredentials).filter(
            BetfairCredentials.user_id == current_user.id
        ).first()

        if not credentials:
            return CredentialsStatusResponse(
                is_configured=False,
                has_app_key=False,
                has_certificate=False,
                username=None
            )

        # Decrypt username for display
        username = None
        if credentials.username_encrypted:
            try:
                username = encryption_service.decrypt(credentials.username_encrypted)
            except:
                pass

        return CredentialsStatusResponse(
            is_configured=credentials.is_configured,
            has_app_key=bool(credentials.app_key_encrypted),
            has_certificate=bool(credentials.cert_encrypted),
            username=username
        )

    except Exception as e:
        logger.error(f"Error getting credentials status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Eroare la verificarea statusului"
        )


@router.delete("/credentials")
async def delete_betfair_credentials(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete user's Betfair credentials

    Returns:
        success: bool
        message: str
    """
    try:
        credentials = db.query(BetfairCredentials).filter(
            BetfairCredentials.user_id == current_user.id
        ).first()

        if credentials:
            db.delete(credentials)
            db.commit()
            logger.info(f"Deleted Betfair credentials for user {current_user.email}")

            return {
                "success": True,
                "message": "Credențiale Betfair șterse cu succes"
            }
        else:
            return {
                "success": False,
                "message": "Nu există credențiale de șters"
            }

    except Exception as e:
        logger.error(f"Error deleting Betfair credentials: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Eroare la ștergerea credențialelor"
        )

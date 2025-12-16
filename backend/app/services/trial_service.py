"""
Trial service for managing user trials
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

from app.models.user import User

logger = logging.getLogger(__name__)


class TrialService:
    """Service for trial management"""

    @staticmethod
    def check_subscription_expired(user: User) -> bool:
        """
        Check if user's subscription has expired (works for ALL plans including trial)

        Args:
            user: User object

        Returns:
            True if subscription expired, False otherwise
        """
        # Check subscription_ends_at (universal pentru toate planurile)
        if not user.subscription_ends_at:
            return False

        return datetime.utcnow() > user.subscription_ends_at

    @staticmethod
    def check_trial_expired(user: User) -> bool:
        """
        DEPRECATED: Use check_subscription_expired instead
        Check if user's trial has expired

        Args:
            user: User object

        Returns:
            True if trial expired, False otherwise
        """
        return TrialService.check_subscription_expired(user)

    @staticmethod
    def suspend_expired_subscriptions(db: Session) -> int:
        """
        Suspend all users with expired subscriptions (ALL plans)

        Args:
            db: Database session

        Returns:
            Number of users suspended
        """
        # Find all users with expired subscriptions (orice plan)
        expired_users = db.query(User).filter(
            and_(
                User.subscription_status.in_(["trial", "active"]),
                User.subscription_ends_at < datetime.utcnow()
            )
        ).all()

        count = 0
        for user in expired_users:
            user.subscription_status = "suspended"
            user.is_active = False
            logger.info(f"Suspended user {user.email} - subscription expired")
            count += 1

        if count > 0:
            db.commit()
            logger.info(f"Suspended {count} users with expired trials")

        return count

    @staticmethod
    def get_days_remaining(user: User) -> int:
        """
        Get number of days remaining in subscription (works for ALL plans)

        Args:
            user: User object

        Returns:
            Days remaining (0 if expired or no subscription)
        """
        if not user.subscription_ends_at:
            return 0

        delta = user.subscription_ends_at - datetime.utcnow()
        days = delta.days

        return max(0, days)

    @staticmethod
    def get_trial_days_remaining(user: User) -> int:
        """
        DEPRECATED: Use get_days_remaining instead
        """
        return TrialService.get_days_remaining(user)

    @staticmethod
    def activate_subscription(
        db: Session,
        user_id: str,
        plan_name: str,
        max_teams: int
    ) -> User:
        """
        Activate paid subscription for user (upgrade from trial)

        Args:
            db: Database session
            user_id: User ID
            plan_name: Plan name (simplu, comun, extrem, premium)
            max_teams: Max teams for plan

        Returns:
            Updated User object
        """
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise ValueError("User not found")

        # Update subscription
        user.subscription_plan = plan_name
        user.subscription_status = "active"
        user.max_teams = max_teams
        user.trial_ends_at = None  # Clear trial end date
        user.subscription_ends_at = datetime.utcnow() + timedelta(days=30)  # 30 days for paid plans
        user.is_active = True

        db.commit()
        db.refresh(user)

        logger.info(f"Activated {plan_name} subscription for user {user.email}")

        return user


# Singleton instance
trial_service = TrialService()

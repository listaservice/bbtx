"""
Subscription model
"""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    # Primary Key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)

    # Stripe
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    stripe_price_id = Column(String(255), nullable=True)

    # Subscription Details
    plan_name = Column(String(50), nullable=False)  # simplu, comun, extrem, premium
    plan_price = Column(Float, nullable=False)  # 49, 75, 150, 250
    max_teams = Column(Integer, nullable=False)  # 5, 10, 25, unlimited (-1)

    # Status
    status = Column(String(50), default="active")  # active, cancelled, past_due, trialing

    # Billing Period
    current_period_start = Column(DateTime, nullable=True)
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(String(50), default="false")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="subscription")

    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, plan={self.plan_name}, status={self.status})>"

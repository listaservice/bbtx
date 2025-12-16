"""
User model
"""
from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"

    # Primary Key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Authentication
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    # Profile
    full_name = Column(String(255), nullable=True)

    # Subscription
    subscription_plan = Column(String(50), default="demo")  # demo, simplu, comun, extrem, premium
    subscription_status = Column(String(50), default="trial")  # trial, active, inactive, suspended, cancelled, past_due
    max_teams = Column(Integer, default=5)  # Based on plan (demo = 5)
    trial_ends_at = Column(DateTime, nullable=True)  # Trial expiration date (doar pentru demo)
    subscription_ends_at = Column(DateTime, nullable=True)  # Subscription expiration (pentru toate planurile)

    # Google Sheets
    google_sheets_id = Column(String(255), nullable=True)  # Spreadsheet ID per user

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    betfair_credentials = relationship("BetfairCredentials", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, plan={self.subscription_plan})>"

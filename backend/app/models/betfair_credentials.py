"""
Betfair Credentials model (encrypted)
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class BetfairCredentials(Base):
    __tablename__ = "betfair_credentials"

    # Primary Key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign Key
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)

    # Betfair Credentials (ENCRYPTED!)
    app_key_encrypted = Column(Text, nullable=True)  # Delayed App Key
    username_encrypted = Column(Text, nullable=True)
    password_encrypted = Column(Text, nullable=True)

    # SSL Certificate (ENCRYPTED!)
    cert_encrypted = Column(Text, nullable=True)  # Certificate content
    key_encrypted = Column(Text, nullable=True)   # Private key content

    # Status
    is_configured = Column(String(50), default="false")  # true/false
    last_verified = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="betfair_credentials")

    def __repr__(self):
        return f"<BetfairCredentials(id={self.id}, user_id={self.user_id}, configured={self.is_configured})>"

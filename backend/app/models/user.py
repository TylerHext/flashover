"""User model for storing Strava authentication data."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """
    User model representing a Strava user.

    Stores OAuth tokens and user identification for accessing Strava API.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    strava_id = Column(Integer, unique=True, nullable=False, index=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    token_expiry = Column(DateTime, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    activities = relationship("Activity", back_populates="user", cascade="all, delete-orphan")
    sync_log = relationship("SyncLog", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, strava_id={self.strava_id})>"

    @property
    def is_token_expired(self) -> bool:
        """Check if the access token has expired."""
        return datetime.utcnow() >= self.token_expiry

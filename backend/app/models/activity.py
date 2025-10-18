"""Activity model for storing Strava activity data."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.database import Base


class Activity(Base):
    """
    Activity model representing a Strava activity.

    Stores activity metadata and encoded polyline for map rendering.
    """
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    strava_activity_id = Column(Integer, unique=True, nullable=False, index=True)

    # Activity details
    name = Column(String, nullable=False)
    type = Column(String, nullable=False, index=True)  # Run, Ride, Walk, etc.
    start_date = Column(DateTime, nullable=False, index=True)
    distance = Column(Float, nullable=False)  # Distance in meters
    polyline = Column(Text, nullable=True)  # Encoded polyline from Strava

    # Additional data (stored as JSON) - for elevation, moving_time, etc.
    extra_data = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="activities")

    def __repr__(self):
        return f"<Activity(id={self.id}, strava_id={self.strava_activity_id}, type={self.type}, name='{self.name}')>"

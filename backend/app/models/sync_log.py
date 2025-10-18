"""SyncLog model for tracking activity synchronization."""
from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class SyncLog(Base):
    """
    SyncLog model for tracking when user activities were last synced.

    Used to implement incremental sync - only fetch new activities since last sync.
    """
    __tablename__ = "sync_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    last_sync = Column(DateTime, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sync_log")

    def __repr__(self):
        return f"<SyncLog(user_id={self.user_id}, last_sync={self.last_sync})>"

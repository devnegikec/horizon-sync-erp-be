"""System Configuration model for application settings"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, String, Text

from app.database import Base


class SystemConfig(Base):
    """System Configuration model for storing application settings"""

    __tablename__ = "system_config"

    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)

    # Audit fields
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    updated_by = Column(String(100), nullable=False)

    def __repr__(self):
        return f"<SystemConfig(key='{self.key}', value='{self.value}')>"

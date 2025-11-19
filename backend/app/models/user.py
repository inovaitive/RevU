from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for SSO users
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="user")  # admin, pm, cs, support, executive, developer
    is_active = Column(Boolean, default=True)

    # OAuth fields
    oauth_provider = Column(String(50), nullable=True)  # google, microsoft, email
    oauth_id = Column(String(255), nullable=True)  # Provider's user ID

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization = relationship("Organization", back_populates="users")
    reviewed_analyses = relationship("Analysis", back_populates="reviewer", foreign_keys="Analysis.reviewed_by")

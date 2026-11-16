from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.db.base import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    github_repo_id = Column(Integer, unique=True, nullable=False, index=True)
    full_name = Column(String, nullable=False)      # e.g. "owner/repo-name"
    is_active = Column(Boolean, default=True)       # CodeSheriff enabled/disabled
    created_at = Column(DateTime(timezone=True), server_default=func.now())

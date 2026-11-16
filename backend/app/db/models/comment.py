from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.db.base import Base


class ReviewComment(Base):
    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("pr_reviews.id"), nullable=False)
    file_path = Column(String, nullable=False)
    line_number = Column(Integer, nullable=True)
    # Severity: error | warning | info
    severity = Column(String, default="warning")
    # Category: syntax | style | security | complexity | documentation
    category = Column(String, default="style")
    message = Column(Text, nullable=False)
    suggestion = Column(Text, nullable=True)        # optional fix suggestion
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# db/models/report.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey
from src.db import Base
import uuid


class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id: Mapped[str] = mapped_column(String, ForeignKey("reviews.review_id"), unique=True, nullable=False)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    growth_points: Mapped[str | None] = mapped_column(Text, nullable=True)
    dynamics: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    analytics_for_reviewers: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)

    review = relationship("Review", back_populates="report")
# db/models/question_bank.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, Enum, Boolean, ForeignKey, DateTime, UniqueConstraint, func
from src.db import Base
from src.db.models.user import User
from src.db.models.question import QuestionType
import uuid

class QuestionTemplate(Base):
    __tablename__ = "question_templates"

    question_template_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_by_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), nullable=False, index=True)

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)
    category: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_by = relationship("User")
    options = relationship("QuestionTemplateOption", back_populates="question_template",
                           cascade="all, delete-orphan", order_by="QuestionTemplateOption.position")

class QuestionTemplateOption(Base):
    __tablename__ = "question_template_options"

    option_template_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_template_id: Mapped[str] = mapped_column(String, ForeignKey("question_templates.question_template_id"), nullable=False, index=True)

    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    question_template = relationship("QuestionTemplate", back_populates="options")

class QuestionBlock(Base):
    __tablename__ = "question_blocks"

    block_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_by_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_by = relationship("User")
    items = relationship("QuestionBlockItem", back_populates="block", cascade="all, delete-orphan",
                         order_by="QuestionBlockItem.position")

class QuestionBlockItem(Base):
    __tablename__ = "question_block_items"

    block_id: Mapped[str] = mapped_column(String, ForeignKey("question_blocks.block_id"), primary_key=True)
    question_template_id: Mapped[str] = mapped_column(String, ForeignKey("question_templates.question_template_id"), primary_key=True)

    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    block = relationship("QuestionBlock", back_populates="items")
    question_template = relationship("QuestionTemplate")

    __table_args__ = (
        UniqueConstraint("block_id", "position", name="uq_block_position"),
    )
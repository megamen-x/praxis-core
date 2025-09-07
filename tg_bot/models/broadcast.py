from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey, DateTime, Integer
from datetime import datetime
from db.session import Base
import uuid

class Broadcast(Base):
    __tablename__ = 'broadcasts'
    
    id = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_text = mapped_column(String, nullable=False)
    scheduled_time = mapped_column(DateTime(timezone=True), nullable=False)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    status = mapped_column(String(20), default='scheduled')  # scheduled, completed, failed
    sent_count = mapped_column(Integer, default=0)
    failed_count = mapped_column(Integer, default=0)

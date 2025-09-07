from sqlalchemy.orm import mapped_column
from sqlalchemy import String, Text, Integer, DateTime
from datetime import datetime
from db import Base

class Broadcast(Base):
    __tablename__ = "broadcasts"

    id = mapped_column(Integer, primary_key=True, index=True)
    message_text = mapped_column(Text, nullable=False)
    scheduled_time = mapped_column(DateTime, nullable=False)
    status = mapped_column(String, default="scheduled")  # scheduled, in_progress, completed, failed
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    sent_count = mapped_column(Integer, default=0)
    failed_count = mapped_column(Integer, default=0)

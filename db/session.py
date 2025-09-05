# db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
LocalSession = sessionmaker(autoflush=False, bind=engine)

def get_db():
    db = LocalSession()
    try:
        yield db
    finally:
        db.close()
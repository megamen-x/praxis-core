#!/usr/bin/env python
from app.db.session import SessionLocal, Base, engine
from app.models import User

def get_or_create(db, email, **kwargs):
    obj = db.query(User).filter(User.email == email).first()
    if obj:
        return obj
    obj = User(email=email, **kwargs)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        hr = get_or_create(db, "hr@example.com", first_name="Hannah", last_name="HR", department="HR", can_create_review=True)
        subject = get_or_create(db, "subject@example.com", first_name="Sam", last_name="Subject", department="R&D")
        reviewer = get_or_create(db, "reviewer@example.com", first_name="Rita", last_name="Reviewer", department="R&D")

        print("Seeded users:")
        print(f"HR user_id:       {hr.user_id}")
        print(f"Subject user_id:  {subject.user_id}")
        print(f"Reviewer user_id: {reviewer.user_id}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
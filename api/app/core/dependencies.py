# dependencies.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import SessionLocal

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_service(db: Session = Depends(get_db)):
    from app.auth.services import UserService
    return UserService(db)
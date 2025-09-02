from fastapi import Depends
from sqlalchemy.orm import Session
from app.auth.services import UserService
from app.documents.services import DocumentService
from app.core.database import SessionLocal
from app.core.security import oauth2_scheme


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_user_service(db: Session = Depends(get_db)):
    from app.auth.services import UserService
    return UserService(db)

def get_document_service():
    return DocumentService()

def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_svc: UserService = Depends(get_user_service)
) -> str:
    """Dependency to get current user from access token"""
    return user_svc.verify_access_token(token)
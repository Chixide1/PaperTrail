from datetime import timedelta
from app.auth.schema import Token
from app.core.database import User
from sqlalchemy.orm import Session
from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, verify_password


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str):
        return self.db.query(User).filter(User.username == username).first()
    
    def create_user(self, username: str, hashedPassword: str):
        exists = self.get_by_username(username)

        if exists:
            return False
        
        user = User(username=username, hashedPassword=hashedPassword)
        self.db.add(user)
        self.db.commit()
        return True
    
    def authenticate_user(self, username: str, password: str):
        user = self.get_by_username(username)

        if not user or not verify_password(password, user.hashed_password):
            return None
        else:
            return user
    
    def create_access_token(self, username: str):
        access_token = create_access_token(
            data={"sub": username},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return Token(
            access_token=access_token,
            token_type="bearer"
        )
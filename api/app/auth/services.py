from datetime import datetime, timedelta, timezone
from typing import Optional
from app.auth.schema import TokenResponse
from app.core.database import User
from app.core.exceptions import CredentialsException
from sqlalchemy.orm import Session
from jwt import decode, PyJWTError # type: ignore
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES, 
    JWTPayload, 
    SECRET_KEY, 
    ALGORITHM,
    create_jwt_token, 
    verify_password
)


class UserService:
    def __init__(self, db: Session):
        self.db = db

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()
    
    def create_user(self, username: str, hashedPassword: str) -> bool:
        exists = self.get_by_username(username)

        if exists:
            return False
        
        user = User(
            username=username,
            hashed_password=hashedPassword,
            last_password_change=datetime.now(timezone.utc)
        )
        self.db.add(user)
        self.db.commit()
        return True
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        user = self.get_by_username(username)

        if not user or not verify_password(password, user.hashed_password):
            return None
        else:
            return user
    
    def verify_access_token(self, token: str) -> str:
        """Verify access token and return username"""
        try:
            payload: JWTPayload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            username = payload.get("sub")
            expiry = payload.get("exp")
            issued_at = payload.get("iat")
            token_type = payload.get("typ")

            now = datetime.now(timezone.utc).timestamp()
            
            # Check basic token validity (expiry, type)
            if token_type != "access" or expiry < now:
                raise CredentialsException()
            
            # Now check if user exists and password hasn't changed
            user = self.get_by_username(username)
            if not user:
                raise CredentialsException()
            
            # Validate token was issued after last password change
            if issued_at < user.last_password_change.timestamp():
                raise CredentialsException()
            
            return username
            
        except PyJWTError:
            raise CredentialsException()
    
    def verify_refresh_token(self, token: str) -> str:
        """Verify refresh token and return username"""
        try:
            # First, verify the signature and basic token validity
            payload: JWTPayload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            username = payload.get("sub")
            expiry = payload.get("exp")
            issued_at = payload.get("iat")
            token_type = payload.get("typ")
            
            if not username:
                raise CredentialsException()
            
            now = datetime.now(timezone.utc).timestamp()
            
            # Check basic token validity (expiry, type)
            if token_type != "refresh" or expiry < now:
                raise CredentialsException()
            
            # Now check if user exists and password hasn't changed
            user = self.get_by_username(username)
            if not user:
                raise CredentialsException()
            
            # Validate token was issued after last password change
            if issued_at < user.last_password_change.timestamp():
                raise CredentialsException()
                
            return username
            
        except PyJWTError:
            raise CredentialsException()
    
    def refresh_access_token(self, refresh_token: str) -> Optional[TokenResponse]:
        """Create new access token from valid refresh token"""
        try:
            # Verify the refresh token (this also checks user existence)
            verified_username = self.verify_refresh_token(refresh_token)
            
            # Create new access token
            access_token = create_jwt_token(
                data={"sub": verified_username, "typ": "access"},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            return TokenResponse(access_token=access_token)
            
        except CredentialsException:
            return None
        except Exception:
            return None
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change user password and update last_password_change timestamp"""
        user = self.authenticate_user(username, old_password)
        if not user:
            return False
        
        from app.core.security import hash_password
        user.hashed_password = hash_password(new_password)
        user.last_password_change = datetime.now(timezone.utc)
        
        self.db.commit()
        return True
    
    def invalidate_all_tokens(self, username: str) -> bool:
        """Invalidate all tokens for a user by updating last_password_change"""
        user = self.get_by_username(username)
        if not user:
            return False
        
        user.last_password_change = datetime.now(timezone.utc)
        self.db.commit()
        return True
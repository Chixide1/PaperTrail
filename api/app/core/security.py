from typing import Any, Literal, TypedDict
from fastapi import Depends
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from jwt import encode, decode, PyJWTError # type: ignore
from datetime import datetime, timedelta, timezone
from app.core.exceptions import CredentialsException
from app.core.config import settings
import uuid

class JWTPayload(TypedDict):
    jti: uuid.UUID # Unique ID
    sub: str  # Subject (username)
    exp: float # Expiration time
    iat: float # Issued at time
    typ: Literal["access", "refresh"]

SECRET_KEY = settings.JWT_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", refreshUrl="auth/refresh")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt_token(data: dict[str, Any], expires_delta: timedelta | None = None):
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=15))

    payload: dict[str, Any] = {
        "jti": str(uuid.uuid4()),
        "exp": expire.timestamp(),
        "iat": now.timestamp()
    }
    payload.update(data)
    return encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(
    last_password_change: datetime,
    token: str = Depends(oauth2_scheme),
) -> str:
    try:
        payload: JWTPayload = decode(token, settings.JWT_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        expiry = payload.get("exp")
        issued_at = payload.get("iat")

        now = datetime.now(timezone.utc).timestamp()

        if expiry < now or issued_at < last_password_change.timestamp():
            raise CredentialsException()
        
        return username
    except PyJWTError:
        raise CredentialsException()
    
def verify_refresh_token(
    last_password_change: datetime,
    token: str
) -> str:
    """Verify refresh token and return username"""

    try:
        payload: JWTPayload = decode(token, SECRET_KEY, algorithms=[ALGORITHM]) # type: ignore
        username = payload.get("sub")
        expiry = payload.get("exp")
        issued_at = payload.get("iat")
        token_type = payload.get("typ")
        
        now = datetime.now(timezone.utc).timestamp()

        if token_type != "refresh" or expiry < now or issued_at < last_password_change.timestamp():
            raise CredentialsException()
                
        return username
    except PyJWTError:
        raise CredentialsException()
from datetime import timedelta
from venv import logger
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.schema import Token
from app.auth.services import UserService
from app.core.dependencies import get_current_user, get_user_service
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES, 
    REFRESH_TOKEN_EXPIRE_DAYS, 
    create_jwt_token, 
    hash_password
)

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.post("/register")
def register(
    username: str,
    password: str,
    user_svc: UserService = Depends(get_user_service)
):
    try:
        result = user_svc.create_user(username, hash_password(password))

        if not result:
            return {"msg": f"That username is already taken, try another one!"}
        return {"msg": f"Your account has been successfully registered!"}
    except Exception as e:
        logger.error(e)
        raise HTTPException(500, "An Error occurred while attempting to register your user")

@router.post("/login", response_model=Token)
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_svc: UserService = Depends(get_user_service)
):
    user = user_svc.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    refresh_token = create_jwt_token(
        data={"sub": user.username, "typ": "refresh"},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/auth/refresh" 
    )

    access_token = create_jwt_token(
        data={"sub": user.username, "typ": "access"},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return Token(access_token=access_token)

@router.post("/refresh")
def refresh_token(
    request: Request,
    user_svc: UserService = Depends(get_user_service)
):
    """Refresh access token using refresh token"""
    try:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Missing refresh token")

        new_token = user_svc.refresh_access_token(refresh_token)
        if not new_token:
            raise HTTPException(
                status_code=401, 
                detail="Invalid refresh token or user no longer exists"
            )
        return new_token
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=401, 
            detail="Could not refresh token"
        )

@router.post("/logout")
def logout(
    current_user: str = Depends(get_current_user),
    user_svc: UserService = Depends(get_user_service)
):
    """Logout user by invalidating all tokens"""
    user_svc.invalidate_all_tokens(current_user)
    return {"message": "Successfully logged out"}

@router.post("/change-password")
def change_password(
    old_password: str,
    new_password: str,
    current_user: str = Depends(get_current_user),
    user_svc: UserService = Depends(get_user_service)
):
    """Change user password"""
    success = user_svc.change_password(current_user, old_password, hash_password(new_password))
    if not success:
        raise HTTPException(status_code=400, detail="Invalid current password")
    return {"message": "Password changed successfully"}

@router.get("/protected")
def protected_route(current_user: str = Depends(get_current_user)):
    return {"message": f"Hello, {current_user}!"}
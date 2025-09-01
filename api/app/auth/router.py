from venv import logger
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.auth.services import UserService
from app.core.dependencies import get_user_service
from app.core.security import get_current_user, hash_password

router = APIRouter(
    prefix="/auth"
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

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_svc: UserService = Depends(get_user_service)
):
    user = user_svc.authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user_svc.create_access_token(user.username) # type: ignore

@router.get("/protected")
def protected_route(current_user: str = Depends(get_current_user)):
    return {"message": f"Hello, {current_user}!"}
"""
routers/users.py — User registration, login, logout, and profile endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

import database
import sessions
import validation
from schemas import UserCreate, UserLogin, UserResponse
from utils import hash_password, verify_password

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate):
    """Register a new user account."""
    validation.validate_email_format(body.email)
    validation.validate_password_strength(body.password)

    pool = await database.get_pool()

    if await database.get_user_by_email(pool, body.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    pw_hash = hash_password(body.password)
    user = await database.create_user(pool, body.email, pw_hash)
    return UserResponse(**user)


@router.post("/login", response_model=UserResponse)
async def login(body: UserLogin, response: Response):
    """Authenticate a user and issue a signed session cookie."""
    pool = await database.get_pool()
    user = await database.get_user_by_email(pool, body.email)

    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = sessions.create_token(str(user["id"]), user["email"])
    sessions.set_session_cookie(response, token)
    return UserResponse(**user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response):
    """Clear the session cookie (logout)."""
    sessions.clear_session_cookie(response)


@router.get("/me", response_model=UserResponse)
async def me(request: Request, current_user: dict = Depends(sessions.get_current_user)):
    """Return the currently authenticated user profile."""
    pool = await database.get_pool()
    user = await database.get_user_by_id(pool, current_user["sub"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserResponse(**user)

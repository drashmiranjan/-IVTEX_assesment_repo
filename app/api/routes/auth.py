from fastapi import APIRouter, HTTPException, status, Depends

from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.user_service import create_user, login_user
from app.api.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return current_user

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(user_data: UserCreate):
    try:
        return await create_user(user_data)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

@router.post("/login")
async def login(user_data: UserLogin):
    try:
        return await login_user(
            email=user_data.email,
            password=user_data.password,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

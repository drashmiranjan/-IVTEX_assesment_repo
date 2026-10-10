
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

from app.api.dependencies import require_roles
from app.schemas.user import UserRole
from app.services.user_management_service import (
    list_users,
    get_user_by_id,
    update_user,
    set_user_active_status,
    delete_user,
)


router = APIRouter(
    prefix="/users",
    tags=["User Management"],
)


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserStatusUpdate(BaseModel):
    is_active: bool


@router.get("/")
async def get_users(
    search: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    sort_by: Literal[
        "name", "email", "role", "created_at", "updated_at"
    ] = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    current_user=Depends(require_roles("admin")),
):
    try:
        return await list_users(
            search=search,
            role=role.value if role else None,
            is_active=is_active,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get("/{user_id}")
async def get_user(
    user_id: str,
    current_user=Depends(require_roles("admin")),
):
    try:
        return await get_user_by_id(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.patch("/{user_id}")
async def patch_user(
    user_id: str,
    user_data: UserUpdate,
    current_user=Depends(require_roles("admin")),
):
    updates = user_data.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one field to update",
        )

    try:
        if "role" in updates and updates["role"] is not None:
            updates["role"] = updates["role"].value

        return await update_user(user_id, updates)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.patch("/{user_id}/status")
async def change_user_status(
    user_id: str,
    status_data: UserStatusUpdate,
    current_user=Depends(require_roles("admin")),
):
    try:
        return await set_user_active_status(
            user_id,
            status_data.is_active,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.delete("/{user_id}")
async def remove_user(
    user_id: str,
    current_user=Depends(require_roles("admin")),
):
    if user_id == current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    try:
        return await delete_user(user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

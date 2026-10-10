
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.schemas.activity import (
    ActivityCreate,
    ActivityUpdate,
    ActivityResponse,
)
from app.services.activity_service import (
    create_activity,
    list_activities,
    get_activity_by_id,
    update_activity,
    delete_activity,
)

router = APIRouter(prefix="/activities", tags=["Activity Management"])


@router.post("/", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity_endpoint(
    activity_data: ActivityCreate,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await create_activity(activity_data, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/")
async def list_activities_endpoint(
    activity_status: str | None = Query(default=None, alias="status"),
    activity_type: str | None = None,
    related_type: str | None = None,
    related_id: str | None = None,
    assigned_to: str | None = None,
    overdue_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await list_activities(
            current_user=current_user,
            status=activity_status,
            activity_type=activity_type,
            related_type=related_type,
            related_id=related_id,
            assigned_to=assigned_to,
            overdue_only=overdue_only,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity_endpoint(
    activity_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await get_activity_by_id(activity_id, current_user)
    except ValueError as exc:
        message = str(exc)
        error_status = 404 if message in {
            "Invalid activity ID",
            "Activity not found",
        } else 400
        raise HTTPException(status_code=error_status, detail=message)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.patch("/{activity_id}", response_model=ActivityResponse)
async def update_activity_endpoint(
    activity_id: str,
    activity_data: ActivityUpdate,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await update_activity(activity_id, activity_data, current_user)
    except ValueError as exc:
        message = str(exc)
        error_status = 404 if message in {
            "Invalid activity ID",
            "Activity not found",
        } else 400
        raise HTTPException(status_code=error_status, detail=message)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/{activity_id}")
async def delete_activity_endpoint(
    activity_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await delete_activity(activity_id, current_user)
    except ValueError as exc:
        message = str(exc)
        error_status = 404 if message in {
            "Invalid activity ID",
            "Activity not found",
        } else 400
        raise HTTPException(status_code=error_status, detail=message)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

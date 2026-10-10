
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.schemas.lead import LeadCreate, LeadUpdate,  LeadConversionRequest 
from app.services.conversion_service import convert_lead
from app.services.lead_service import (
    create_lead,
    get_lead_by_id,
    list_leads,
    update_lead,
)


router = APIRouter(prefix="/leads", tags=["Lead Management"])


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_lead(
    lead_data: LeadCreate,
    current_user=Depends(get_current_user),
):
    try:
        return await create_lead(lead_data, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/")
async def get_leads(
    search: str | None = None,
    lead_status: str | None = Query(default=None, alias="status"),
    priority: Literal["low", "medium", "high"] | None = None,
    source: str | None = None,
    assigned_to: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user=Depends(get_current_user),
):
    try:
        return await list_leads(
            current_user=current_user,
            search=search,
            status=lead_status,
            priority=priority,
            source=source,
            assigned_to=assigned_to,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{lead_id}")
async def get_lead(
    lead_id: str,
    current_user=Depends(get_current_user),
):
    try:
        return await get_lead_by_id(lead_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.patch("/{lead_id}")
async def patch_lead(
    lead_id: str,
    lead_data: LeadUpdate,
    current_user=Depends(get_current_user),
):
    try:
        return await update_lead(lead_id, lead_data, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.post("/{lead_id}/convert", status_code=status.HTTP_201_CREATED)
async def convert_lead_endpoint(
    lead_id: str,
    conversion_data: LeadConversionRequest,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await convert_lead(
            lead_id=lead_id,
            deal_title=conversion_data.deal_title,
            deal_value=conversion_data.deal_value,
            deal_probability=conversion_data.deal_probability,
            current_user=current_user,
        )
    except ValueError as exc:
        message = str(exc)
        error_status = (
            404 if message == "Lead not found"
            else 409 if "already been converted" in message or "being converted" in message
            else 400
        )
        raise HTTPException(status_code=error_status, detail=message)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except RuntimeError:
        raise HTTPException(
            status_code=500,
            detail="Lead conversion failed. Please try again.",
        )


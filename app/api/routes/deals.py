
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.schemas.deal import DealCreate, DealUpdate, DealResponse
from app.services.deal_service import (
    create_deal,
    list_deals,
    get_deal_by_id,
    update_deal,
    delete_deal,
)

router = APIRouter(prefix="/deals", tags=["Deal Management"])


@router.post("/", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
async def create_deal_endpoint(
    deal_data: DealCreate,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await create_deal(deal_data, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/")
async def list_deals_endpoint(
    search: str | None = None,
    stage: str | None = None,
    assigned_to: str | None = None,
    customer_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await list_deals(
            current_user=current_user,
            search=search,
            stage=stage,
            assigned_to=assigned_to,
            customer_id=customer_id,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal_endpoint(
    deal_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await get_deal_by_id(deal_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.patch("/{deal_id}", response_model=DealResponse)
async def update_deal_endpoint(
    deal_id: str,
    deal_data: DealUpdate,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await update_deal(deal_id, deal_data, current_user)
    except ValueError as exc:
        message = str(exc)
        error_status = 404 if message in {
            "Invalid deal ID",
            "Deal not found",
        } else 400
        raise HTTPException(status_code=error_status, detail=message)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/{deal_id}")
async def delete_deal_endpoint(
    deal_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await delete_deal(deal_id, current_user)
    except ValueError as exc:
        message = str(exc)
        error_status = 404 if message in {
            "Invalid deal ID",
            "Deal not found",
        } else 400
        raise HTTPException(status_code=error_status, detail=message)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

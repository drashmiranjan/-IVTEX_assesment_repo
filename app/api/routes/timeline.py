
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.services.audit_service import get_entity_timeline

router = APIRouter(prefix="/timeline", tags=["Timeline & Audit"])


@router.get("/{entity_type}/{entity_id}")
async def get_timeline_endpoint(
    entity_type: Literal["lead", "customer", "deal"],
    entity_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await get_entity_timeline(
            entity_type=entity_type,
            entity_id=entity_id,
            current_user=current_user,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        message = str(exc)
        error_status = (
            404
            if message in {
                "Lead not found",
                "Customer not found",
                "Deal not found",
            }
            else 400
        )
        raise HTTPException(status_code=error_status, detail=message)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user
from app.services.analytics_service import get_sales_analytics

router = APIRouter(prefix="/analytics", tags=["Sales Analytics"])


@router.get("/sales")
async def sales_analytics_endpoint(
    current_user: dict = Depends(get_current_user),
):
    try:
        return await get_sales_analytics(current_user)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to generate sales analytics",
        )

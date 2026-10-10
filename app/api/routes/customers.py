
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_current_user
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
)
from app.services.customer_service import (
    create_customer,
    list_customers,
    get_customer_by_id,
    update_customer,
    delete_customer,
)

router = APIRouter(prefix="/customers", tags=["Customer Management"])


@router.post("/", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_endpoint(
    customer_data: CustomerCreate,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await create_customer(customer_data, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/")
async def list_customers_endpoint(
    search: str | None = None,
    customer_status: str | None = Query(default=None, alias="status"),
    assigned_to: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    try:
        return await list_customers(
            current_user=current_user,
            search=search,
            status=customer_status,
            assigned_to=assigned_to,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer_endpoint(
    customer_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await get_customer_by_id(customer_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.patch("/{customer_id}", response_model=CustomerResponse)
async def update_customer_endpoint(
    customer_id: str,
    customer_data: CustomerUpdate,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await update_customer(customer_id, customer_data, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.delete("/{customer_id}")
async def delete_customer_endpoint(
    customer_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        return await delete_customer(customer_id, current_user)
    except ValueError as exc:
        message = str(exc)
        error_status = 404 if message in {
            "Invalid customer ID",
            "Customer not found",
        } else 400
        raise HTTPException(status_code=error_status, detail=message)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))

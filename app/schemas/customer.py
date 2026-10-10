
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=150)
    address: str | None = Field(default=None, max_length=500)


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    company: str | None = Field(default=None, max_length=150)
    address: str | None = Field(default=None, max_length=500)


class CustomerResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    email: EmailStr | None = None
    phone: str | None = None
    company: str | None = None
    address: str | None = None
    original_lead_id: str | None = None
    assigned_to: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

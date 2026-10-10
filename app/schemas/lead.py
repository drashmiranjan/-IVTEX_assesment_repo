
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class LeadStatus(str, Enum):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    CONVERTED = "converted"


class LeadSource(str, Enum):
    WEBSITE = "website"
    REFERRAL = "referral"
    LINKEDIN = "linkedin"
    COLD_CALL = "cold_call"
    ADVERTISEMENT = "advertisement"
    OTHER = "other"


class LeadPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str | None = None
    phone: str | None = None
    company: str | None = Field(default=None, max_length=150)
    source: LeadSource = LeadSource.OTHER
    priority: LeadPriority = LeadPriority.MEDIUM
    notes: str | None = Field(default=None, max_length=2000)


class LeadUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    email: str | None = None
    phone: str | None = None
    company: str | None = Field(default=None, max_length=150)
    source: LeadSource | None = None
    priority: LeadPriority | None = None
    status: LeadStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


class LeadResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    source: LeadSource
    priority: LeadPriority
    status: LeadStatus
    assigned_to: str | None = None
    created_by: str
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadConversionRequest(BaseModel):
    deal_title: str = Field(min_length=2, max_length=150)
    deal_value: float = Field(gt=0)
    deal_probability: int = Field(default=50, ge=0, le=100)

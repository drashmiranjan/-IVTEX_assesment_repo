
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class DealStage(str, Enum):
    QUALIFICATION = "qualification"
    DISCOVERY = "discovery"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"


class DealCreate(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    customer_id: str
    value: float = Field(gt=0)
    probability: int = Field(default=0, ge=0, le=100)
    stage: DealStage = DealStage.QUALIFICATION
    expected_close_date: datetime | None = None
    lost_reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)


class DealUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=150)
    value: float | None = Field(default=None, gt=0)
    probability: int | None = Field(default=None, ge=0, le=100)
    stage: DealStage | None = None
    expected_close_date: datetime | None = None
    lost_reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)


class DealResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    customer_id: str
    assigned_to: str
    created_by: str
    value: float
    probability: int
    expected_revenue: float
    stage: DealStage
    expected_close_date: datetime | None = None
    actual_close_date: datetime | None = None
    lost_reason: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ActivityType(str, Enum):
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    TASK = "task"
    FOLLOW_UP = "follow_up"


class ActivityStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class RelatedEntityType(str, Enum):
    LEAD = "lead"
    CUSTOMER = "customer"
    DEAL = "deal"


class ActivityCreate(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    activity_type: ActivityType
    due_date: datetime
    related_type: RelatedEntityType
    related_id: str
    assigned_to: str | None = None


class ActivityUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    activity_type: ActivityType | None = None
    due_date: datetime | None = None
    status: ActivityStatus | None = None
    assigned_to: str | None = None


class ActivityResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    title: str
    description: str | None = None
    activity_type: ActivityType
    status: ActivityStatus
    due_date: datetime
    related_type: RelatedEntityType
    related_id: str
    assigned_to: str
    created_by: str
    completed_at: datetime | None = None
    is_overdue: bool
    created_at: datetime
    updated_at: datetime

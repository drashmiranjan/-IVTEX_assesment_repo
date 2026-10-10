
from datetime import datetime
from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    id: str
    actor_id: str
    action: str
    entity_type: str
    entity_id: str
    details: dict = Field(default_factory=dict)
    created_at: datetime

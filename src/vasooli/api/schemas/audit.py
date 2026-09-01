from pydantic import BaseModel, ConfigDict
from datetime import datetime

class AuditLogRead(BaseModel):
    id: int
    record_id: str
    step: str
    detail: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

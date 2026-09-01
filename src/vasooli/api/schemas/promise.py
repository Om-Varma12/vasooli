from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class PromiseToPayRead(BaseModel):
    id: int
    record_id: str
    customer_id: str
    promised_amount: float
    promised_date: Optional[datetime] = None
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

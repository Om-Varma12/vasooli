from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class RecoveryEventBase(BaseModel):
    record_id: str
    customer_id: str
    merchant_id: Optional[str] = None
    amount_inr: float
    root_cause: str
    channel: str
    tier: str
    status: str
    retry_count_so_far: Optional[int] = 0
    message_or_transcript: Optional[str] = None
    reason: Optional[str] = None
    amount_recovered_inr: float = 0.0
    promise_captured: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RecoveryEventRead(RecoveryEventBase):
    pass

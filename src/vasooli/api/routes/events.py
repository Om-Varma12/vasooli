from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional, List
import base64
from datetime import datetime

from ..deps import get_db
from ..models import RecoveryEvent, PromiseToPay, AuditLog
from ..schemas.event import RecoveryEventRead
from ..schemas.common import PaginatedResponse
from ..schemas.promise import PromiseToPayRead

router = APIRouter(prefix="/recovery-events", tags=["Recovery Events"])

@router.get("/", response_model=PaginatedResponse[RecoveryEventRead])
async def get_recovery_events(
    status: Optional[str] = None,
    root_cause: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    cursor: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch a paginated list of recovery events using keyset pagination.
    """
    query = select(RecoveryEvent).order_by(desc(RecoveryEvent.created_at), desc(RecoveryEvent.record_id))

    if status:
        query = query.where(RecoveryEvent.status == status)
    if root_cause:
        query = query.where(RecoveryEvent.root_cause == root_cause)

    # Keyset pagination implementation
    if cursor:
        try:
            # Cursor is encoded as "timestamp|record_id"
            decoded_cursor = base64.b64decode(cursor).decode("utf-8").split("|")
            cursor_time = datetime.fromisoformat(decoded_cursor[0])
            cursor_id = decoded_cursor[1]

            query = query.where(
                (RecoveryEvent.created_at < cursor_time) |
                ((RecoveryEvent.created_at == cursor_time) & (RecoveryEvent.record_id < cursor_id))
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid pagination cursor")

    # Fetch limit + 1 to determine if there's a next page
    result = await db.execute(query.limit(limit + 1))
    events = result.scalars().all()

    has_next = len(events) > limit
    items = events[:limit]

    next_cursor = None
    if has_next:
        last_item = items[-1]
        cursor_str = f"{last_item.created_at.isoformat()}|{last_item.record_id}"
        next_cursor = base64.b64encode(cursor_str.encode()).decode()

    # Get total count for the current filters
    count_query = select(func.count()).select_from(RecoveryEvent)
    if status:
        count_query = count_query.where(RecoveryEvent.status == status)
    if root_cause:
        count_query = count_query.where(RecoveryEvent.root_cause == root_cause)

    total_count = (await db.execute(count_query)).scalar() or 0

    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        total_count=total_count
    )

@router.get("/{record_id}", response_model=RecoveryEventRead)
async def get_event_detail(record_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RecoveryEvent).where(RecoveryEvent.record_id == record_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Recovery event not found")
    return event

@router.get("/{record_id}/audit", response_model=List[AuditLogRead]) # Need to define AuditLogRead in response_model
async def get_event_audit(
    record_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    # Import AuditLogRead inside to avoid circular imports if any
    from ..schemas.audit import AuditLogRead

    query = select(AuditLog).where(AuditLog.record_id == record_id).order_by(AuditLog.created_at.asc())
    result = await db.execute(query.limit(limit))
    return result.scalars().all()

@router.get("/{record_id}/promises", response_model=List[PromiseToPayRead])
async def get_event_promises(record_id: str, db: AsyncSession = Depends(get_db)):
    query = select(PromiseToPay).where(PromiseToPay.record_id == record_id)
    result = await db.execute(query)
    return result.scalars().all()

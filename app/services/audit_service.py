import json
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    user_id: Optional[int],
    action: str,
    resource: str,
    resource_id: Optional[str] = None,
    details: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=json.dumps(details, ensure_ascii=False) if details else None,
        ip_address=ip_address,
    )
    db.add(log)
    await db.flush()
    return log

"""Audit trail: single choke point for every mutation. Never raise to callers."""
from datetime import datetime, timezone
from typing import Any, Optional

from backend.core.firebase import get_db


def write_audit_log(
    entity_id: str,
    entity_type: str,
    action: str,
    before_state: Optional[dict[str, Any]],
    after_state: Optional[dict[str, Any]],
) -> None:
    """Write one audit entry. Best-effort: logging failures must not break requests."""
    try:
        get_db().collection("audit_log").add(
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "action": action,
                "before_state": before_state,
                "after_state": after_state,
                "timestamp": datetime.now(timezone.utc),
            }
        )
    except Exception:
        pass

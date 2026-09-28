"""Feature 12: global audit trail queries."""
from typing import Optional

from fastapi import APIRouter

from backend.core.firebase import get_db
from backend.core.firestore_utils import doc_to_dict

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
async def list_audit(
    entity_id: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 200,
) -> list[dict]:
    db = get_db()
    coll = db.collection("audit_log")
    query = coll
    if entity_id:
        query = query.where("entity_id", "==", entity_id)
    if entity_type:
        query = query.where("entity_type", "==", entity_type)
    limit = max(1, min(limit, 500))
    return [doc_to_dict(d) for d in query.limit(limit).stream()]

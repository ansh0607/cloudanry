"""Feature 5: semantic keyword search endpoint (embeddings-swappable)."""
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from backend.services.search import search_media

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("")
async def search_endpoint(
    q: str = Query(..., min_length=1),
    project_id: Optional[str] = None,
) -> dict[str, Any]:
    try:
        results = search_media(q, project_id=project_id)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    return {"query": q, "count": len(results), "results": results}

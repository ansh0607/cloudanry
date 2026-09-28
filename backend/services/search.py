"""Media search.

Hackathon scope: case-insensitive keyword/substring match over ai_tags,
cloudinary tags and image_description.

The public interface `search_media(query, project_id=None)` is intentionally
backend-agnostic: swap `keyword_search` for an embeddings implementation later
(e.g. score = cosine(query_embedding, tag_embedding)) without touching callers.
"""
from typing import Any, Optional

from backend.core.firebase import get_db


def _normalize(text: str) -> str:
    return (text or "").lower().strip()


def _matches(query: str, text: Optional[str]) -> bool:
    return query in _normalize(text or "")


def _score_item(query: str, item: dict[str, Any]) -> float:
    """Higher is better: tags count 2x, description 1x."""
    score = 0.0
    tags = list(item.get("ai_tags") or []) + list(item.get("cloudinary_tags") or [])
    for tag in tags:
        if _matches(query, str(tag)):
            score += 2.0
    if _matches(query, item.get("image_description")):
        score += 1.0
    return score


def keyword_search(items: list[dict[str, Any]], query: str) -> list[dict[str, Any]]:
    """Pure function: rank items by simple keyword/substring score. Testable."""
    q = _normalize(query)
    if not q:
        return []
    scored = []
    for item in items:
        s = _score_item(q, item)
        if s > 0:
            scored.append((s, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored]


def search_media(query: str, project_id: Optional[str] = None, limit: int = 100) -> list[dict[str, Any]]:
    """Search stored media. Currently keyword backend; embeddings drop-in later."""
    db = get_db()
    coll = db.collection("media")
    if project_id:
        docs = coll.where("project_id", "==", project_id).limit(limit).stream()
    else:
        docs = coll.limit(limit).stream()
    items = []
    for doc in docs:
        data = doc.to_dict() | {"id": doc.id}
        items.append(data)
    return keyword_search(items, query)

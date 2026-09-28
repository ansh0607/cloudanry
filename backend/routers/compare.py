"""Feature 6: before/after comparison endpoint."""
import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.firebase import get_db
from backend.core.firestore_utils import doc_to_dict
from backend.services.compare import compare_media, log_comparison

router = APIRouter(prefix="/api/compare", tags=["compare"])


class CompareIn(BaseModel):
    media_id_a: str
    media_id_b: str


def _get_media(media_id: str) -> dict:
    doc = get_db().collection("media").document(media_id).get()
    if not doc.exists:
        raise HTTPException(404, f"Media {media_id} not found")
    return doc_to_dict(doc)


async def _fetch_bytes(url: str) -> bytes:
    if not url:
        raise HTTPException(400, "Media has no downloadable URL")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Could not download media: {e}")


@router.post("")
async def compare_endpoint(body: CompareIn) -> dict:
    media_a = _get_media(body.media_id_a)
    media_b = _get_media(body.media_id_b)

    if media_a.get("project_id") != media_b.get("project_id"):
        raise HTTPException(400, "Both media items must belong to the same project")

    # Earlier capture = "before"
    date_a = media_a.get("capture_date") or ""
    date_b = media_b.get("capture_date") or ""
    if date_a and date_b and date_a > date_b:
        media_a, media_b = media_b, media_a

    bytes_a = await _fetch_bytes(media_a.get("cloudinary_url") or "")
    bytes_b = await _fetch_bytes(media_b.get("cloudinary_url") or "")

    result = compare_media(media_a, media_b, bytes_a, bytes_b)
    result["project_id"] = media_a.get("project_id")
    result["media_a"] = _summary(media_a)
    result["media_b"] = _summary(media_b)
    log_comparison(media_a.get("project_id"), result)
    return result


def _summary(m: dict) -> dict:
    return {
        "id": m.get("id"),
        "cloudinary_url": m.get("cloudinary_url"),
        "thumbnail_url": m.get("thumbnail_url"),
        "capture_date": m.get("capture_date"),
    }

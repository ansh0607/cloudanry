"""Feature 11: one-click shareable HTML report endpoint."""
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from backend.core.firebase import get_db
from backend.core.firestore_utils import doc_to_dict
from backend.services.compare import compare_media
from backend.services.report import generate_report

router = APIRouter(prefix="/api/projects", tags=["report"])


async def _download(url: str) -> Optional[bytes]:
    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except httpx.HTTPError:
        return None


def _pick_before_after(media: list[dict[str, Any]]):
    """Earliest vs latest dated media as the default before/after pair."""
    dated = sorted([m for m in media if m.get("capture_date")], key=lambda m: m["capture_date"])
    if len(dated) >= 2:
        return dated[0], dated[-1]
    return None, None


@router.get("/{project_id}/report", response_class=HTMLResponse)
async def project_report(project_id: str) -> HTMLResponse:
    db = get_db()

    proj_doc = db.collection("projects").document(project_id).get()
    if not proj_doc.exists:
        raise HTTPException(404, "Project not found")
    project = doc_to_dict(proj_doc)

    media = [
        doc_to_dict(d)
        for d in db.collection("media").where("project_id", "==", project_id).limit(300).stream()
    ]
    claims = [
        doc_to_dict(d)
        for d in db.collection("claims").where("project_id", "==", project_id).limit(100).stream()
    ]

    media_a, media_b = _pick_before_after(media)
    comparison = None
    if media_a and media_b:
        bytes_a = await _download(media_a.get("cloudinary_url") or "")
        bytes_b = await _download(media_b.get("cloudinary_url") or "")
        if bytes_a and bytes_b:
            comparison = compare_media(media_a, media_b, bytes_a, bytes_b)

    html = generate_report(project, media, claims, comparison, media_a, media_b)
    return HTMLResponse(content=html)

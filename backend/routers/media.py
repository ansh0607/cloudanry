"""Features 2, 3, 12: upload pipeline, media gallery, per-media audit history."""
import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.core.audit import write_audit_log
from backend.core.cloudinary_client import (
    extract_capture_date,
    extract_gps,
    extract_video_frames,
    upload_media,
)
from backend.core.config import get_settings
from backend.core.demo_media import save_upload as demo_save_upload
from backend.core.firebase import get_db
from backend.core.firestore_utils import doc_to_dict
from backend.services.dedup import compute_phash, find_near_duplicates, log_duplicate_flag
from backend.services.relevance import score_relevance

router = APIRouter(prefix="/api/media", tags=["media"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fetch_media(media_id: str) -> dict[str, Any]:
    doc = get_db().collection("media").document(media_id).get()
    if not doc.exists:
        raise HTTPException(404, "Media not found")
    return doc_to_dict(doc)


def _fetch_project(project_id: str) -> dict[str, Any]:
    doc = get_db().collection("projects").document(project_id).get()
    if not doc.exists:
        raise HTTPException(404, "Project not found")
    return doc_to_dict(doc)


def _thumb_or_url(media: dict[str, Any]) -> str:
    return media.get("thumbnail_url") or media.get("cloudinary_url") or ""


def _vision_url(media: dict[str, Any]) -> str:
    """URL fed to the vision model: the ORIGINAL upload, NO Cloudinary transforms.

    Verified Sep 2026: Cloudinary re-encodes transformed variants (q_auto OR any
    c_limit/w_* resize) of small images into palette-mode files that the vision
    encoder reads as noise (the model "sees" grids of white lines on black).
    Thumbnails stay fine for UI display; the model must get original bytes.
    """
    return media.get("cloudinary_url") or media.get("thumbnail_url") or ""


async def _download_image(url: str) -> Optional[tuple[bytes, str]]:
    """Fetch an image (or video frame) so it can be sent to the vision model."""
    import httpx

    if not url:
        return None
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            mime = resp.headers.get("content-type", "image/jpeg").split(";")[0]
            return resp.content, mime
    except Exception:
        return None


async def _collect_frames(project: dict[str, Any], media: dict[str, Any]) -> list[tuple[bytes, str]]:
    """1 image for photos; up to N sampled frames for videos."""
    settings = get_settings()
    frames: list[tuple[bytes, str]] = []
    if media.get("media_type") == "video":
        urls = extract_video_frames(media.get("cloudinary_public_id", ""), "video")
        for url in urls[: settings.max_frames_per_video]:
            fetched = await _download_image(url)
            if fetched:
                frames.append(fetched)
    else:
        fetched = await _download_image(_vision_url(media))
        if fetched:
            frames.append(fetched)
    return frames


@router.post("/upload", status_code=201)
async def upload_endpoint(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    capture_date: Optional[str] = Form(None),
    gps: Optional[str] = Form(None),
) -> dict[str, Any]:
    """Feature 2: upload -> Cloudinary -> EXIF/GPS -> phash -> relevance -> Firestore.

    gps: optional JSON string {"lat": .., "lng": ..} supplied by the client when
    the file itself has no GPS EXIF (e.g. web capture).
    """
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit")

    project = _fetch_project(project_id)

    # 1. Store media: Cloudinary in normal mode, local files in demo mode
    try:
        if settings.demo_mode:
            up = demo_save_upload(data, file.filename or "upload")
        else:
            up = upload_media(data, file.filename or "upload")
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:  # Cloudinary SDK errors (auth, rate limits, network)
        raise HTTPException(502, f"Media upload failed: {e}")

    exif_raw = up.get("exif") or {}
    gps_data = extract_gps(exif_raw)
    if not gps_data and gps:
        try:
            parsed = json.loads(gps)
            if isinstance(parsed, dict) and parsed.get("lat") is not None and parsed.get("lng") is not None:
                gps_data = {"lat": float(parsed["lat"]), "lng": float(parsed["lng"])}
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    capture = capture_date or extract_capture_date(exif_raw)
    resource_type = up.get("resource_type", "image")

    # 2. Perceptual hash + duplicate scan across ALL projects (feature 7)
    phash_value = None
    duplicate_matches: list[dict[str, Any]] = []
    if resource_type == "image":
        try:
            phash_value = compute_phash(data)
            duplicate_matches = find_near_duplicates(phash_value)
        except Exception:
            phash_value = None

    media_doc = {
        "project_id": project_id,
        "cloudinary_url": up.get("secure_url"),
        "cloudinary_public_id": up.get("public_id"),
        "thumbnail_url": (up.get("eager") or [{}])[0].get("secure_url"),
        "media_type": "video" if resource_type == "video" else "image",
        "capture_date": capture,
        "gps": gps_data,
        "exif_raw": exif_raw,
        "ai_tags": [],
        "cloudinary_tags": up.get("tags") or [],
        "image_description": None,
        "relevance_score": None,
        "relevance_reasoning": None,
        "phash": phash_value,
        "duplicate_matches": duplicate_matches,
        "uploaded_at": _now(),
    }

    # 3. Relevance scoring via vision model (feature 4) — best effort
    try:
        frames = await _collect_frames(project, media_doc)
        relevance = await score_relevance(project, frames) if frames else None
    except Exception:
        relevance = None
    if relevance:
        media_doc.update(
            {
                "image_description": relevance.get("image_description"),
                "relevance_score": relevance.get("relevance_score"),
                "relevance_reasoning": relevance.get("reasoning"),
                "relevance_model": relevance.get("model"),
                "location_match": relevance.get("location_match"),
                "content_match": relevance.get("content_match"),
            }
        )

    # 4. Persist + audit
    ref = get_db().collection("media").add(media_doc)[1]
    media_id = ref.id
    write_audit_log(media_id, "media", "upload", None, {k: v for k, v in media_doc.items() if k != "exif_raw"})
    log_duplicate_flag(media_id, duplicate_matches)

    return {"id": media_id, **{k: v for k, v in media_doc.items() if k != "exif_raw"}}


@router.get("")
async def list_media(
    project_id: Optional[str] = None,
    group_by: str = "date",
) -> dict[str, Any]:
    """Feature 3: gallery data. Grouping done server-side so the UI stays dumb.

    group_by: "date" (YYYY-MM-DD) or "location" (rounded GPS grid).
    """
    db = get_db()
    coll = db.collection("media")
    query = coll.where("project_id", "==", project_id) if project_id else coll
    items = [doc_to_dict(d) for d in query.limit(500).stream()]

    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        if group_by == "location":
            gps = item.get("gps") or {}
            if gps:
                key = f"{round(gps['lat'], 2)}, {round(gps['lng'], 2)}"
            else:
                key = "No GPS data"
        else:
            key = (item.get("capture_date") or "unknown date")[:10]
        groups.setdefault(key, []).append(item)

    return {
        "group_by": group_by,
        "total": len(items),
        "groups": [
            {"key": k, "count": len(v), "items": v} for k, v in sorted(groups.items(), reverse=True)
        ],
    }


@router.get("/{media_id}")
async def get_media(media_id: str) -> dict[str, Any]:
    return _fetch_media(media_id)


@router.get("/{media_id}/audit")
async def get_media_audit(media_id: str) -> list[dict[str, Any]]:
    """Feature 12: full history of one media item (newest first)."""
    _fetch_media(media_id)  # 404 if missing
    logs = (
        get_db()
        .collection("audit_log")
        .where("entity_id", "==", media_id)
        .limit(200)
        .stream()
    )
    return [doc_to_dict(d) for d in logs]

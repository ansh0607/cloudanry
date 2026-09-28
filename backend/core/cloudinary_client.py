"""Cloudinary wrapper: upload, EXIF/GPS extraction, auto-tagging, video frames.

Uses the cloudinary Python SDK. All calls are sync (SDK is blocking) but wrapped
so the FastAPI handlers can offload them to a thread if needed.
"""
from typing import Any, Optional

from backend.core.config import get_settings


def _sdk():
    settings = get_settings()
    if not settings.cloudinary_configured:
        raise RuntimeError(
            "Cloudinary is not configured. Set CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY "
            "and CLOUDINARY_API_SECRET in .env (see .env.example)."
        )
    import cloudinary
    import cloudinary.uploader

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    return cloudinary


def upload_media(file_bytes: bytes, filename: str, resource_type: str = "auto") -> dict[str, Any]:
    """Upload raw bytes to Cloudinary. Returns the raw upload response dict.

    - context/exif: request EXIF data back
    - categorization: addinfo -> triggers Cloudinary AI auto-tagging
    - detection: captioning is a paid add-on; we do NOT rely on it (our own
      vision model handles descriptions).
    """
    cloudinary = _sdk()
    base_kwargs: dict[str, Any] = dict(
        public_id=None,
        filename=filename,
        resource_type=resource_type,
        exif=True,
        colors=True,
        eager=[{"width": 640, "crop": "limit", "quality": "auto"}],  # thumbnail-ish
    )
    try:
        # categorization + auto_tagging need the Google Auto Tagging add-on
        # (paid). If the plan lacks it, retry without AI tagging.
        return cloudinary.uploader.upload(
            file_bytes,
            categorization="google_tagging",
            auto_tagging=0.6,
            **base_kwargs,
        )
    except Exception as e:
        if "tag" in str(e).lower() or "ratelimited" in type(e).__name__.lower():
            return cloudinary.uploader.upload(file_bytes, **base_kwargs)
        raise


def extract_gps(exif: dict[str, Any]) -> Optional[dict[str, float]]:
    """Convert Cloudinary EXIF GPS fields (DMS rational strings) to decimal degrees."""
    try:
        lat = _dms_to_decimal(exif.get("GPSLatitude"), exif.get("GPSLatitudeRef"))
        lng = _dms_to_decimal(exif.get("GPSLongitude"), exif.get("GPSLongitudeRef"))
        if lat is None or lng is None:
            return None
        return {"lat": round(lat, 6), "lng": round(lng, 6)}
    except Exception:
        return None


def _dms_to_decimal(dms: Any, ref: Optional[str]) -> Optional[float]:
    if not dms:
        return None
    parts = [float(p) for p in str(dms).split(",")] if isinstance(dms, str) else list(dms)
    deg, minutes, seconds = (parts + [0, 0, 0])[:3]
    value = deg + minutes / 60.0 + seconds / 3600.0
    if ref in ("S", "W"):
        value = -value
    return value


def extract_capture_date(exif: dict[str, Any]) -> Optional[str]:
    """Pull DateTimeOriginal (or fallbacks) as ISO date string."""
    for key in ("DateTimeOriginal", "CreateDate", "DateTime", "ModifyDate"):
        raw = exif.get(key)
        if raw:
            try:
                # Typical EXIF format: "2025:03:14 10:22:31"
                cleaned = str(raw).replace(":", "-", 2).replace(" ", "T")
                return cleaned[:19]
            except Exception:
                continue
    return None


def extract_video_frames(public_id: str, resource_type: str = "video") -> list[str]:
    """Return 1-3 cloudinary image URLs for frames sampled from a video.

    Cloudinary serves video frames by appending image transforms to the
    video public_id (e.g. .jpg at a timestamp offset).
    """
    settings = get_settings()
    base = f"https://res.cloudinary.com/{settings.cloudinary_cloud_name}/{resource_type}/upload"
    offsets = [0.5, 3.0, 6.0]
    return [
        f"{base}/so_{offset},w_768,c_limit,f_jpg/{public_id}.jpg" for offset in offsets
    ][: settings.max_frames_per_video]

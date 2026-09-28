"""Local media storage for DEMO_MODE (stands in for Cloudinary uploads).

Files land in backend/core/demo_media/uploads/ and are served by FastAPI's
StaticFiles mount at /demo-files. URLs are absolute (PUBLIC_BASE_URL, default
http://localhost:8000) so the frontend, the compare downloader and the report
generator can all fetch them unchanged.
"""
import re
import uuid
from pathlib import Path
from typing import Any

from backend.core.config import get_settings

DEMO_DIR = Path(__file__).resolve().parent / "demo_media"

_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff")
_VIDEO_EXTS = (".mp4", ".mov", ".webm", ".avi", ".mkv")


def ensure_dirs() -> Path:
    """Create uploads dir (and a .gitignore so generated files stay untracked)."""
    uploads = DEMO_DIR / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    gitignore = DEMO_DIR / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text("uploads/\n", encoding="utf-8")
    return uploads


def _safe_name(filename: str) -> str:
    base = Path(filename.replace("\\", "/")).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._") or "upload"
    return cleaned[:60]


def save_upload(data: bytes, filename: str) -> dict[str, Any]:
    """Persist bytes locally and return a Cloudinary-upload-shaped dict."""
    uploads = ensure_dirs()
    name = f"{uuid.uuid4().hex[:8]}_{_safe_name(filename)}"
    (uploads / name).write_bytes(data)
    url = f"{get_settings().public_base_url}/demo-files/{name}"
    lower = name.lower()
    if lower.endswith(_VIDEO_EXTS):
        resource_type = "video"
    elif lower.endswith(_IMAGE_EXTS):
        resource_type = "image"
    else:
        resource_type = "image"  # demo focuses on images; unknown types ride along
    return {
        "secure_url": url,
        "public_id": name,
        "resource_type": resource_type,
        "eager": [{"secure_url": url}],
        "exif": {},  # local demo files have no EXIF; client-supplied GPS/date still apply
        "tags": [],
    }

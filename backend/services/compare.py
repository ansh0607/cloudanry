"""Deterministic before/after image comparison.

Simple color-threshold metrics with Pillow + NumPy — no ML, runs in well under
2 seconds on typical field photos (downscaled to 512px for speed).
"""
import io
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
from PIL import Image

from backend.core.audit import write_audit_log

# Green-dominance thresholds (RGB)
G_MIN, G_MAX = 40, 220
R_MAX = 200
B_MAX = 200


def _load_rgb(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")
    img.thumbnail((512, 512))
    return img


def green_pixel_ratio(data: bytes) -> float:
    """Fraction of pixels that look 'vegetation green' (0.0 - 1.0)."""
    arr = np.asarray(_load_rgb(data), dtype=np.int16)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    mask = (g >= G_MIN) & (g <= G_MAX) & (g > r) & (g > b) & (r <= R_MAX) & (b <= B_MAX)
    return float(mask.mean())


def pixel_diff_percent(data_a: bytes, data_b: bytes) -> float:
    """Mean absolute channel difference between two images, as 0-100 percent.

    Images are aligned to a common canvas first (they may be different sizes).
    """
    a = _load_rgb(data_a)
    b = _load_rgb(data_b)
    w = min(a.width, b.width)
    h = min(a.height, b.height)
    a = a.resize((w, h))
    b = b.resize((w, h))
    arr_a = np.asarray(a, dtype=np.int16)
    arr_b = np.asarray(b, dtype=np.int16)
    diff = np.abs(arr_a - arr_b).mean()
    return float(diff / 255.0 * 100.0)


def compare_media(
    media_a: dict[str, Any],
    media_b: dict[str, Any],
    bytes_a: bytes,
    bytes_b: bytes,
) -> dict[str, Any]:
    """Build the full before/after comparison payload.

    media_a is expected to be the EARLIER capture ('before'), media_b the later.
    """
    ratio_a = green_pixel_ratio(bytes_a)
    ratio_b = green_pixel_ratio(bytes_b)
    diff = pixel_diff_percent(bytes_a, bytes_b)

    ordered = [media_a.get("capture_date") or "", media_b.get("capture_date") or ""]
    chronological = bool(ordered[0] and ordered[1] and ordered[0] <= ordered[1])

    return {
        "media_a_id": media_a.get("id"),
        "media_b_id": media_b.get("id"),
        "capture_date_a": media_a.get("capture_date"),
        "capture_date_b": media_b.get("capture_date"),
        "chronological_order": chronological,
        "green_ratio_a": round(ratio_a, 4),
        "green_ratio_b": round(ratio_b, 4),
        "green_ratio_delta": round(ratio_b - ratio_a, 4),
        "green_ratio_delta_percent": round((ratio_b - ratio_a) * 100.0, 2),
        "pixel_diff_percent": round(diff, 2),
        "metric": "green-pixel ratio delta (vegetation proxy) + mean pixel diff",
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def log_comparison(project_id: Optional[str], result: dict[str, Any]) -> None:
    write_audit_log(
        entity_id=f"{result['media_a_id']}__{result['media_b_id']}",
        entity_type="comparison",
        action="compare",
        before_state={"media_id": result["media_a_id"]},
        after_state={
            "media_id": result["media_b_id"],
            "project_id": project_id,
            "green_ratio_delta_percent": result["green_ratio_delta_percent"],
            "pixel_diff_percent": result["pixel_diff_percent"],
        },
    )

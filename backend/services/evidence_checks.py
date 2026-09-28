"""Deterministic evidence checks over a claim's linked media (no AI).

- EXIF timestamp/GPS consistency vs the project location and across media.
- These results are fed to BOTH AI roles and to the UI.
"""
import math
from datetime import datetime
from typing import Any


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def check_exif_consistency(
    linked_media: list[dict[str, Any]],
    project: dict[str, Any],
    gps_tolerance_km: float = 50.0,
) -> dict[str, Any]:
    """Verify capture dates/GPS across a claim's linked media.

    Never asserts truth — only reports mechanical metadata consistency.
    """
    issues: list[dict[str, Any]] = []
    notes: list[str] = []

    dates = []
    proj_loc = (project.get("location") or {})
    proj_lat, proj_lng = proj_loc.get("lat"), proj_loc.get("lng")

    for m in linked_media:
        mid = m.get("id", "?")
        dt = _parse_date(m.get("capture_date"))
        if dt:
            dates.append(dt)
        else:
            issues.append({"media_id": mid, "type": "missing_capture_date", "detail": "No EXIF capture date stored"})

        gps = m.get("gps") or {}
        if not gps:
            issues.append({"media_id": mid, "type": "missing_gps", "detail": "No GPS metadata stored"})
        elif proj_lat is not None and proj_lng is not None:
            dist = haversine_km(float(gps["lat"]), float(gps["lng"]), float(proj_lat), float(proj_lng))
            if dist > gps_tolerance_km:
                issues.append(
                    {
                        "media_id": mid,
                        "type": "gps_far_from_project",
                        "detail": f"{dist:.0f} km from project location (tolerance {gps_tolerance_km:.0f} km)",
                    }
                )
            else:
                notes.append(f"{mid}: GPS {dist:.0f} km from project location — consistent")

    date_span_days = None
    if len(dates) >= 2:
        span = (max(dates) - min(dates)).days
        date_span_days = span
        notes.append(f"Capture dates span {span} days across linked media")

    return {
        "check": "exif_timestamp_gps_consistency",
        "consistent": len(issues) == 0,
        "issues": issues,
        "notes": notes,
        "date_span_days": date_span_days,
        "media_checked": len(linked_media),
    }


def dedup_signals_from(matches_by_media: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Turn duplicate-scan results into ready-made adversarial signals."""
    signals = []
    for media_id, matches in matches_by_media.items():
        for match in matches:
            if match.get("media_id") == media_id:
                continue  # self-match guard
            signals.append(
                {
                    "description": (
                        f"Near-duplicate detected: media {media_id} is "
                        f"{match.get('similarity_percent')}% similar to previously stored media "
                        f"{match.get('media_id')} (project {match.get('project_id')})."
                    ),
                    "severity": "high" if (match.get("similarity_percent") or 0) >= 97 else "medium",
                    "basis": "deterministic_phash_check",
                    "duplicate_media_id": match.get("media_id"),
                }
            )
    return signals

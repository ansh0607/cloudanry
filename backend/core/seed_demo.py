"""Seeds DEMO_MODE with a small, honest sample dataset.

Runs inside the server process on startup when demo_mode is on and the
database is empty (so it survives Freebuff restarts — data re-seeds every boot).

Honesty rules respected:
- Images are synthesized locally (Pillow) and descriptions are prefixed "DEMO".
- AI-produced fields stay empty/None: relevance scoring and dual-AI analysis
  are NOT faked; the claim explains that AI assessment is unavailable.
- The confidence score is computed by the real deterministic scorer.
"""
import io
from datetime import datetime, timezone
from typing import Any

from backend.core.demo_media import save_upload
from backend.core.firebase import get_db

PROJECT_LAT, PROJECT_LNG = 23.2599, 77.4126


def _synth_image(before: bool) -> bytes:
    """Synthesize a hillside photo: dry/brown 'before', green/tree'd 'after'."""
    import random

    from PIL import Image, ImageDraw

    rng = random.Random(7 if before else 11)
    w, h = 640, 420
    img = Image.new("RGB", (w, h), (168, 190, 210))  # sky
    d = ImageDraw.Draw(img)
    d.rectangle([0, h // 3, w, h], fill=(146, 116, 78) if before else (74, 132, 66))
    if before:
        for _ in range(24):  # sparse dry shrubs
            x, y = rng.randint(0, w - 16), rng.randint(h // 3 + 8, h - 12)
            r = rng.randint(3, 7)
            d.ellipse([x, y, x + r * 2, y + r], fill=(104, 96, 52))
    else:
        for _ in range(60):  # rows of young trees
            x, y = rng.randint(10, w - 34), rng.randint(h // 3 + 10, h - 28)
            r = rng.randint(8, 16)
            d.ellipse([x, y, x + r * 2, y + r * 1.4], fill=(36, 96, 42))
            d.rectangle([x + r - 2, y + r * 1.2, x + r + 2, y + r * 1.9], fill=(84, 62, 40))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _media_doc(project_id: str, up: dict[str, Any], spec: dict[str, Any], now: datetime) -> dict[str, Any]:
    from backend.services.dedup import compute_phash

    return {
        "project_id": project_id,
        "cloudinary_url": up["secure_url"],
        "cloudinary_public_id": up["public_id"],
        "thumbnail_url": up["eager"][0]["secure_url"],
        "media_type": "image",
        "capture_date": spec["capture_date"],
        "gps": {"lat": PROJECT_LAT, "lng": PROJECT_LNG},
        "exif_raw": {},
        "ai_tags": [],
        "cloudinary_tags": [],
        "image_description": spec["description"],
        "relevance_score": None,
        "relevance_reasoning": "Relevance scoring unavailable in demo mode (set GROQ_API_KEY for vision scoring).",
        "phash": compute_phash(spec["_bytes"]),
        "duplicate_matches": [],
        "uploaded_at": now,
    }


def seed_if_empty() -> bool:
    """Seed one demo project + media pair + claim. Returns True if it seeded."""
    from backend.core.audit import write_audit_log
    from backend.services.confidence import compute_confidence
    from backend.services.evidence_checks import check_exif_consistency, dedup_signals_from

    db = get_db()
    if any(db.collection("projects").limit(1).stream()):
        return False

    now = datetime.now(timezone.utc)

    project_data: dict[str, Any] = {
        "project_name": "Green Ridge Reforestation (DEMO)",
        "description": (
            "DEMO project: restoring 40 ha of degraded hillside with native species. "
            "Media should show planting activity and vegetation recovery on the ridge."
        ),
        "location": {"place_name": "Green Ridge (demo)", "lat": PROJECT_LAT, "lng": PROJECT_LNG},
        "expected_activity_type": "tree planting",
        "created_at": now,
    }
    project_id = db.collection("projects").add(project_data)[1].id
    write_audit_log(project_id, "project", "create", None, project_data)

    specs = [
        {
            "before": True,
            "capture_date": "2026-01-10T09:30:00",
            "description": "DEMO image: dry degraded hillside before planting; sparse brown vegetation, little canopy.",
        },
        {
            "before": False,
            "capture_date": "2026-09-15T10:05:00",
            "description": "DEMO image: same hillside after two planting seasons; rows of young native trees, green ground cover.",
        },
    ]

    media_ids: list[str] = []
    linked_media: list[dict[str, Any]] = []
    for spec in specs:
        data = _synth_image(spec["before"])
        up = save_upload(data, f"demo_{'before' if spec['before'] else 'after'}.png")
        spec["_bytes"] = data
        media_doc = _media_doc(project_id, up, spec, now)
        media_id = db.collection("media").add(media_doc)[1].id
        media_ids.append(media_id)
        linked_media.append(media_doc | {"id": media_id})
        write_audit_log(media_id, "media", "upload", None, {k: v for k, v in media_doc.items() if k != "exif_raw"})
        write_audit_log(media_id, "media", "duplicate_check", None, {"duplicate_matches": []})

    # Deterministic checks run for real — they need no AI.
    exif_check = check_exif_consistency(linked_media, project_data)
    dup_signals = dedup_signals_from({m["id"]: [] for m in linked_media})

    supporting = [
        {
            "description": "Both linked media carry GPS coordinates matching the project location, with capture dates spanning the claimed planting period (Jan → Sep 2026).",
            "strength": 65,
            "basis": "deterministic_checks",
        },
        {
            "description": "Media descriptions indicate vegetation recovery consistent with the claim (curated demo descriptions, not AI-assessed).",
            "strength": 55,
            "basis": "media_description",
        },
    ]
    adversarial_ai = [
        {
            "description": "AI relevance scoring and dual-AI analysis are unavailable in demo mode (no GROQ_API_KEY): image content is NOT independently assessed.",
            "severity": "medium",
            "basis": "system_limitation",
        }
    ]
    adversarial = dup_signals + adversarial_ai
    scored = compute_confidence(supporting, adversarial)

    claim_doc: dict[str, Any] = {
        "project_id": project_id,
        "claim_text": "DEMO claim: Tree planting on Green Ridge restored vegetation cover between January and September 2026.",
        "linked_media_ids": media_ids,
        "supporting_signals": supporting,
        "adversarial_signals": adversarial,
        "deterministic_checks": {"exif_check": exif_check, "duplicate_signals": dup_signals},
        "confidence_score": scored["confidence_score"],
        "score_breakdown": scored["score_breakdown"],
        "scoring_language": scored["scoring_language"],
        "models_used": {
            "supporting": "demo-mode (Groq not configured)",
            "adversarial": "demo-mode (Groq not configured)",
        },
        "created_at": now,
    }
    claim_id = db.collection("claims").add(claim_doc)[1].id
    write_audit_log(claim_id, "claim", "create", None, {k: v for k, v in claim_doc.items() if k != "score_breakdown"})

    return True

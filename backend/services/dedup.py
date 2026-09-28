"""Perceptual-hash duplicate detection via imagehash (pHash, Hamming distance).

Similarity % = (64 - hamming) / 64 * 100. Threshold ~90% per brief.
Scans across ALL projects so cross-project reuse is caught.
"""
import io
from typing import Any

import imagehash
from PIL import Image


def compute_phash(image_bytes: bytes) -> str:
    """Return hex string perceptual hash of an image."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    return str(imagehash.phash(img))


def hamming_distance(hash_a: str, hash_b: str) -> int:
    return imagehash.hex_to_hash(hash_a) - imagehash.hex_to_hash(hash_b)


def similarity_percent(hash_a: str, hash_b: str) -> float:
    return round((64 - hamming_distance(hash_a, hash_b)) * 100 / 64, 1)


def find_near_duplicates(new_phash: str, threshold_percent: float = 90.0) -> list[dict[str, Any]]:
    """Scan every stored media record that has a phash; return matches >= threshold."""
    from backend.core.firebase import get_db

    db = get_db()
    matches: list[dict[str, Any]] = []
    docs = db.collection("media").where("phash", "!=", None).stream()
    for doc in docs:
        data = doc.to_dict()
        stored = data.get("phash")
        if not stored:
            continue
        similarity = 100.0 if stored == new_phash else similarity_percent(new_phash, stored)
        if similarity >= threshold_percent:
            matches.append(
                {
                    "media_id": doc.id,
                    "project_id": data.get("project_id"),
                    "cloudinary_url": data.get("cloudinary_url"),
                    "stored_phash": stored,
                    "similarity_percent": similarity,
                }
            )
    return matches


def log_duplicate_flag(media_id: str, matches: list[dict[str, Any]]) -> None:
    """Audit-log the outcome of a duplicate scan for one media item."""
    from backend.core.audit import write_audit_log

    write_audit_log(
        entity_id=media_id,
        entity_type="media",
        action="duplicate_check",
        before_state=None,
        after_state={"duplicate_matches": matches},
    )

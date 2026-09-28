"""Features 7-10 backend: claim creation pipeline and claim retrieval.

Claim creation: fetch project + linked media -> deterministic checks (EXIF/GPS
consistency + duplicate flags) -> dual AI in parallel -> deterministic
confidence score -> persist + audit. The score is plain code, never an AI call.
"""
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.audit import write_audit_log
from backend.core.firebase import get_db
from backend.core.firestore_utils import doc_to_dict
from backend.services.confidence import compute_confidence
from backend.services.dual_ai import analyze_claim
from backend.services.evidence_checks import check_exif_consistency, dedup_signals_from

router = APIRouter(prefix="/api/claims", tags=["claims"])


class ClaimIn(BaseModel):
    project_id: str
    claim_text: str
    linked_media_ids: list[str]


def _project_or_404(project_id: str) -> dict[str, Any]:
    doc = get_db().collection("projects").document(project_id).get()
    exists = doc.exists
    if not exists:
        raise HTTPException(404, "Project not found")
    return doc_to_dict(doc)


def _linked_media(ids: list[str]) -> list[dict[str, Any]]:
    db = get_db()
    out: list[dict[str, Any]] = []
    for media_id in ids:
        doc = db.collection("media").document(media_id).get()
        if doc.exists:
            out.append(doc_to_dict(doc))
    return out


def _dup_matches_for(media: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        m["id"]: (m.get("duplicate_matches") or [])
        for m in media
        if m.get("id")
    }


@router.post("", status_code=201)
async def create_claim(body: ClaimIn) -> dict[str, Any]:
    if not body.linked_media_ids:
        raise HTTPException(400, "A claim needs at least one linked media item")
    if not body.claim_text.strip():
        raise HTTPException(400, "claim_text is required")

    project = _project_or_404(body.project_id)
    linked_media = _linked_media(body.linked_media_ids)
    if not linked_media:
        raise HTTPException(400, "None of the linked media items exist")

    # ---- deterministic checks (feature 7) ----
    exif_check = check_exif_consistency(linked_media, project)
    dup_signals = dedup_signals_from(_dup_matches_for(linked_media))
    deterministic = {
        "exif_check": exif_check,
        "duplicate_signals": dup_signals,
    }

    # ---- dual AI in parallel (feature 8) ----
    ai_result = await analyze_claim(body.claim_text.strip(), project, linked_media, deterministic)
    supporting = ai_result["supporting_signals"]
    adversarial = dup_signals + ai_result["adversarial_signals"]

    # ---- deterministic scoring (feature 9) — NOT an AI call ----
    scored = compute_confidence(supporting, adversarial)

    claim_doc = {
        "project_id": body.project_id,
        "claim_text": body.claim_text.strip(),
        "linked_media_ids": body.linked_media_ids,
        "supporting_signals": supporting,
        "adversarial_signals": adversarial,
        "deterministic_checks": deterministic,
        "confidence_score": scored["confidence_score"],
        "score_breakdown": scored["score_breakdown"],
        "scoring_language": scored["scoring_language"],
        "models_used": ai_result["models_used"],
        "created_at": datetime.now(timezone.utc),
    }

    ref = get_db().collection("claims").add(claim_doc)[1]
    write_audit_log(ref.id, "claim", "create", None, {k: v for k, v in claim_doc.items() if k != "score_breakdown"})
    return {"id": ref.id, **claim_doc}


@router.get("")
async def list_claims(project_id: Optional[str] = None) -> list[dict[str, Any]]:
    db = get_db()
    coll = db.collection("claims")
    query = coll.where("project_id", "==", project_id) if project_id else coll
    return [doc_to_dict(d) for d in query.limit(200).stream()]


@router.get("/{claim_id}")
async def get_claim(claim_id: str) -> dict[str, Any]:
    doc = get_db().collection("claims").document(claim_id).get()
    if not doc.exists:
        raise HTTPException(404, "Claim not found")
    return doc_to_dict(dict(doc.to_dict() or {}) | {"id": doc.id})


@router.delete("/{claim_id}", status_code=204)
async def delete_claim(claim_id: str) -> None:
    db = get_db()
    ref = db.collection("claims").document(claim_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(404, "Claim not found")
    before = doc_to_dict(snap)
    ref.delete()
    write_audit_log(claim_id, "claim", "delete", before, None)

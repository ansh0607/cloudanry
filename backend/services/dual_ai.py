"""Dual AI claim analysis: Supporting AI + Adversarial AI run in parallel.

Different Groq models per role. System prompts below are PLACEHOLDERS —
the user will supply final prompts verbatim; replace only the PROMPT strings.
"""
import asyncio
import json
from typing import Any

from backend.core.config import get_settings
from backend.core.groq_client import GroqError, chat_json

# ============================================================================
# PLACEHOLDER PROMPTS — replace verbatim with user-supplied prompts (feature 8)
# ============================================================================

SUPPORTING_SYSTEM_PROMPT = """PLACEHOLDER — Supporting AI.
You assess whether supplied evidence is CONSISTENT WITH an impact claim.
You never claim proof or verification. Use language like "consistent with".
Consider: relevance scores, image descriptions, EXIF/GPS consistency,
duplicate flags. Return ONLY JSON:
{"signals": [{"description": str, "strength": int 0-100, "basis": str}]}
Return {"signals": []} if nothing supports the claim."""

ADVERSARIAL_SYSTEM_PROMPT = """PLACEHOLDER — Adversarial AI.
You actively look for reasons the evidence may NOT support the claim:
low relevance scores, metadata mismatches, duplicates, vague descriptions.
You never call evidence "fake" or "fraud" — use "contradiction detected",
"inconsistency detected", "weak support". Return ONLY JSON:
{"signals": [{"description": str, "severity": "low"|"medium"|"high", "basis": str}]}
Return {"signals": []} if you find no contradictions."""


def _context_for_ai(claim_text: str, project: dict[str, Any], linked_media: list[dict[str, Any]], deterministic: dict[str, Any]) -> str:
    return json.dumps(
        {
            "claim": claim_text,
            "project": {
                "name": project.get("project_name"),
                "description": project.get("description"),
                "location": project.get("location"),
                "expected_activity_type": project.get("expected_activity_type"),
            },
            "linked_media": [
                {
                    "media_id": m.get("id"),
                    "media_type": m.get("media_type"),
                    "capture_date": m.get("capture_date"),
                    "gps": m.get("gps"),
                    "ai_tags": m.get("ai_tags"),
                    "image_description": m.get("image_description"),
                    "relevance_score": m.get("relevance_score"),
                    "relevance_reasoning": m.get("relevance_reasoning"),
                }
                for m in linked_media
            ],
            "deterministic_check_results": deterministic,
        },
        ensure_ascii=False,
        default=str,
    )


async def run_supporting_ai(context_json: str) -> list[dict[str, Any]]:
    settings = get_settings()
    try:
        result = await chat_json(
            messages=[
                {"role": "system", "content": SUPPORTING_SYSTEM_PROMPT},
                {"role": "user", "content": context_json},
            ],
            model=settings.groq_model_supporting,
            temperature=0.2,
            max_tokens=1200,
        )
        return _normalize_supporting(result.get("signals") or [])
    except GroqError as e:
        return [{"description": f"Supporting AI unavailable: {e}", "strength": 0, "basis": "system_error", "is_error": True}]


async def run_adversarial_ai(context_json: str) -> list[dict[str, Any]]:
    settings = get_settings()
    try:
        result = await chat_json(
            messages=[
                {"role": "system", "content": ADVERSARIAL_SYSTEM_PROMPT},
                {"role": "user", "content": context_json},
            ],
            model=settings.groq_model_adversarial,
            temperature=0.2,
            max_tokens=1200,
        )
        return _normalize_adversarial(result.get("signals") or [])
    except GroqError as e:
        return [{"description": f"Adversarial AI unavailable: {e}", "severity": "low", "basis": "system_error", "is_error": True}]


async def analyze_claim(
    claim_text: str,
    project: dict[str, Any],
    linked_media: list[dict[str, Any]],
    deterministic: dict[str, Any],
) -> dict[str, Any]:
    """Run both AI roles in parallel; return raw signal lists + model metadata."""
    context = _context_for_ai(claim_text, project, linked_media, deterministic)
    settings = get_settings()
    supporting, adversarial = await asyncio.gather(
        run_supporting_ai(context),
        run_adversarial_ai(context),
    )
    return {
        "supporting_signals": supporting,
        "adversarial_signals": adversarial,
        "models_used": {
            "supporting": settings.groq_model_supporting,
            "adversarial": settings.groq_model_adversarial,
        },
        "prompts_note": "placeholder prompts in use — replace in backend/services/dual_ai.py",
    }


def _normalize_supporting(signals: list[Any]) -> list[dict[str, Any]]:
    out = []
    for s in signals:
        if not isinstance(s, dict):
            continue
        try:
            strength = max(0, min(100, int(s.get("strength", 0))))
        except (TypeError, ValueError):
            strength = 0
        out.append(
            {
                "description": str(s.get("description", ""))[:300],
                "strength": strength,
                "basis": str(s.get("basis", ""))[:100],
            }
        )
    return out


def _normalize_adversarial(signals: list[Any]) -> list[dict[str, Any]]:
    out = []
    for s in signals:
        if not isinstance(s, dict):
            continue
        severity = str(s.get("severity", "low")).lower()
        if severity not in ("low", "medium", "high"):
            severity = "low"
        out.append(
            {
                "description": str(s.get("description", ""))[:300],
                "severity": severity,
                "basis": str(s.get("basis", ""))[:100],
            }
        )
    return out

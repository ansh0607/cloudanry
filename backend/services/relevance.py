"""Relevance scoring: Groq vision model compares an upload against its project.

Output JSON contract (stored on the media record):
{
  "image_description": str,
  "relevance_score": 0-100,
  "reasoning": str,
  "location_match": bool | "unclear",
  "content_match": bool | "unclear"
}
"""
import json
from typing import Any

from backend.core.config import get_settings
from backend.core.groq_client import GroqError, chat, image_data_url, parse_json_object

SYSTEM_PROMPT = (
    "You are a media-relevance assessor for field evidence in sustainability and "
    "humanitarian projects. You receive a project description/location and one or more "
    "photos. Describe ONLY what is visibly present; never speculate about intent or "
    "authenticity. Judge relevance conservatively."
)

# Verified Sep 2026: with qwen/qwen3.8-27b, putting the JSON contract in the
# USER message (no system message) yields faithful image descriptions; the
# strict system-message variant made the model hallucinate panel layouts.
USER_JSON_CONTRACT = (
    'Reply with ONLY a JSON object: {"image_description": str, "relevance_score": int '
    '(0-100), "reasoning": str, "location_match": true|false|"unclear", '
    '"content_match": true|false|"unclear"}. No extra keys, no commentary.'
)


def _project_context(project: dict[str, Any]) -> str:
    return (
        f"Project name: {project.get('project_name')}\n"
        f"Description: {project.get('description')}\n"
        f"Expected activity type: {project.get('expected_activity_type')}\n"
        f"Location: {json.dumps(project.get('location') or {}, ensure_ascii=False)}\n"
    )


async def score_relevance(
    project: dict[str, Any],
    image_bytes_list: list[tuple[bytes, str]],
) -> dict[str, Any]:
    """Score 1-3 images (video frames allowed) against a project.

    image_bytes_list: list of (bytes, mime) tuples.
    """
    if not image_bytes_list:
        return _fallback("no image frames available", 0)

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        SYSTEM_PROMPT
                        + "\n\n"
                        + _project_context(project)
                        + USER_JSON_CONTRACT
                        + "\n\nAssess the attached image(s)."
                    ),
                }
            ],
        }
    ]
    # image parts appended after the instruction text
    messages[0]["content"].extend(
        [{"type": "image_url", "image_url": {"url": image_data_url(data, mime)}} for data, mime in image_bytes_list[: get_settings().max_frames_per_video]]
    )
    try:
        settings = get_settings()
        # Verified Sep 2026: at temp 0.1 qwen/qwen3.8-27b hallucinates panel/grid
        # layouts for simple images; temp 0.7 reads the same bytes faithfully.
        raw = await chat(messages, model=settings.groq_model_vision, temperature=0.7)
        result = parse_json_object(raw)
    except (GroqError, Exception) as e:
        return _fallback(f"relevance scoring unavailable: {e}", 0)

    if not result:
        return _fallback("vision model returned unparseable output", 0)

    return {
        "image_description": str(result.get("image_description", ""))[:1000],
        "relevance_score": _clamp_score(result.get("relevance_score")),
        "reasoning": str(result.get("reasoning", ""))[:1000],
        "location_match": result.get("location_match", "unclear"),
        "content_match": result.get("content_match", "unclear"),
        "model": get_settings().groq_model_vision,
    }


def _clamp_score(value: Any) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def _fallback(reason: str, score: int) -> dict[str, Any]:
    return {
        "image_description": "",
        "relevance_score": score,
        "reasoning": reason,
        "location_match": "unclear",
        "content_match": "unclear",
        "model": None,
    }

"""Deterministic confidence scoring — plain code, NOT an AI call.

Merges supporting + adversarial signals into one weighted 0-100 score with an
itemized, auditable breakdown. Same inputs always produce the same score.
"""
from datetime import datetime, timezone
from typing import Any

BASE_SCORE = 50.0

# Supporting signal: points = strength(0-100) * WEIGHT_SUPPORTING, capped
WEIGHT_SUPPORTING = 0.15
CAP_SUPPORTING_TOTAL = 40.0

# Adversarial signal: flat deduction by severity, capped
SEVERITY_DEDUCTIONS = {"high": 20.0, "medium": 12.0, "low": 6.0}
CAP_ADVERSARIAL_TOTAL = 50.0  # base 50 - 50 => fully contradicted claims can reach 0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_confidence(
    supporting_signals: list[dict[str, Any]],
    adversarial_signals: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return {confidence_score, score_breakdown, language} for a claim.

    supporting_signals: [{description, strength 0-100, basis?}]
    adversarial_signals: [{description, severity low|medium|high, basis?}]
    """
    breakdown: list[dict[str, Any]] = [
        {"step": "base", "description": "Neutral starting point", "delta": BASE_SCORE}
    ]
    running = BASE_SCORE

    supporting_added = 0.0
    for sig in supporting_signals:
        strength = _clamp(_to_float(sig.get("strength"), 0.0), 0.0, 100.0)
        raw = strength * WEIGHT_SUPPORTING
        allowed = CAP_SUPPORTING_TOTAL - supporting_added
        delta = round(min(raw, max(allowed, 0.0)), 2)
        supporting_added += delta
        running = round(running + delta, 2)
        breakdown.append(
            {
                "step": "supporting",
                "description": str(sig.get("description", ""))[:200],
                "strength": strength,
                "delta": delta,
                "running_total": running,
            }
        )

    adversarial_added = 0.0
    for sig in adversarial_signals:
        severity = str(sig.get("severity", "low")).lower()
        if severity not in SEVERITY_DEDUCTIONS:
            severity = "low"
        raw = SEVERITY_DEDUCTIONS[severity]
        allowed = CAP_ADVERSARIAL_TOTAL - adversarial_added
        delta = round(min(raw, max(allowed, 0.0)), 2)
        adversarial_added += delta
        running = round(running - delta, 2)
        breakdown.append(
            {
                "step": "adversarial",
                "description": str(sig.get("description", ""))[:200],
                "severity": severity,
                "delta": -delta,
                "running_total": running,
            }
        )

    final = _clamp(running, 0.0, 100.0)
    breakdown.append(
        {"step": "final", "description": "Clamped to 0-100", "delta": round(final - running, 2), "running_total": round(final, 2)}
    )

    return {
        "confidence_score": round(final, 1),
        "score_breakdown": breakdown,
        "scoring_language": (
            "Evidence strength assessment, not proof. Score reflects weighted "
            "supporting and adversarial signals at assessment time."
        ),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

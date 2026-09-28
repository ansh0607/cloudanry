"""Firestore doc → JSON-safe dict helpers."""
from datetime import datetime
from typing import Any


def doc_to_dict(doc: Any) -> dict[str, Any]:
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return _jsonify(data)


def _jsonify(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonify(v) for v in value]
    return value

"""Feature 1: Project CRUD."""
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.audit import write_audit_log
from backend.core.firebase import get_db
from backend.core.firestore_utils import doc_to_dict

router = APIRouter(prefix="/api/projects", tags=["projects"])


class LocationIn(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    place_name: Optional[str] = None


class ProjectIn(BaseModel):
    project_name: str
    description: str = ""
    location: Optional[LocationIn] = None
    expected_activity_type: Optional[str] = None


@router.post("", status_code=201)
async def create_project(body: ProjectIn) -> dict[str, Any]:
    db = get_db()
    data = {
        "project_name": body.project_name.strip(),
        "description": body.description.strip(),
        "location": body.location.model_dump() if body.location else None,
        "expected_activity_type": body.expected_activity_type,
        "created_at": datetime.now(timezone.utc),
    }
    ref = db.collection("projects").add(data)[1]
    write_audit_log(ref.id, "project", "create", None, data)
    return {"id": ref.id, **{k: v for k, v in data.items() if k != "created_at"}}


@router.get("")
async def list_projects() -> list[dict[str, Any]]:
    db = get_db()
    docs = db.collection("projects").order_by("created_at", direction="DESCENDING").stream()
    return [doc_to_dict(d) for d in docs]


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict[str, Any]:
    doc = get_db().collection("projects").document(project_id).get()
    if not doc.exists:
        raise HTTPException(404, "Project not found")
    return doc_to_dict(doc)


@router.patch("/{project_id}")
async def update_project(project_id: str, body: ProjectIn) -> dict[str, Any]:
    db = get_db()
    ref = db.collection("projects").document(project_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(404, "Project not found")
    before = doc_to_dict(snap)
    updates: dict[str, Any] = {
        "project_name": body.project_name.strip(),
        "description": body.description.strip(),
        "location": body.location.model_dump() if body.location else None,
        "expected_activity_type": body.expected_activity_type,
        "updated_at": datetime.now(timezone.utc),
    }
    ref.update(updates)
    after = {**before, **{k: v for k, v in updates.items() if k != "updated_at"}}
    write_audit_log(project_id, "project", "update", before, after)
    return after


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    db = get_db()
    ref = db.collection("projects").document(project_id)
    snap = ref.get()
    if not snap.exists:
        raise HTTPException(404, "Project not found")
    before = doc_to_dict(snap)
    ref.delete()
    write_audit_log(project_id, "project", "delete", before, None)

"""Unit tests for the in-memory Firestore stub used by DEMO_MODE."""
from datetime import datetime, timezone

from backend.core.firestore_utils import doc_to_dict
from backend.core.memory_db import MemoryFirestore


def test_add_and_get_roundtrip():
    db = MemoryFirestore()
    ref = db.collection("projects").add({"project_name": "A"})[1]
    snap = db.collection("projects").document(ref.id).get()
    assert snap.exists
    assert snap.to_dict()["project_name"] == "A"


def test_doc_to_dict_jsonifies_datetime():
    db = MemoryFirestore()
    ts = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    ref = db.collection("projects").add({"created_at": ts})[1]
    snap = db.collection("projects").document(ref.id).get()
    data = doc_to_dict(snap)
    assert data["created_at"] == "2026-01-02T03:04:05+00:00"
    assert data["id"] == ref.id


def test_where_equals_filter():
    db = MemoryFirestore()
    c = db.collection("media")
    c.add({"project_id": "p1"})
    c.add({"project_id": "p2"})
    docs = list(c.where("project_id", "==", "p1").stream())
    assert len(docs) == 1
    assert docs[0].to_dict()["project_id"] == "p1"


def test_where_not_equals_none_keeps_set_fields():
    """Firestore's field != null semantics: only docs where the field is set."""
    db = MemoryFirestore()
    c = db.collection("media")
    c.add({"phash": "abc"})
    c.add({"phash": None})
    c.add({})
    docs = list(c.where("phash", "!=", None).stream())
    assert len(docs) == 1
    assert docs[0].to_dict()["phash"] == "abc"


def test_order_by_descending_and_limit():
    db = MemoryFirestore()
    c = db.collection("projects")
    for i, day in enumerate((1, 2, 3)):
        c.add({"n": i, "created_at": datetime(2026, 1, day, tzinfo=timezone.utc)})
    docs = list(c.order_by("created_at", direction="DESCENDING").limit(2).stream())
    assert [d.to_dict()["n"] for d in docs] == [2, 1]


def test_update_and_delete():
    db = MemoryFirestore()
    ref = db.collection("projects").add({"name": "old"})[1]
    db.collection("projects").document(ref.id).update({"name": "new"})
    assert db.collection("projects").document(ref.id).get().to_dict()["name"] == "new"
    db.collection("projects").document(ref.id).delete()
    assert not db.collection("projects").document(ref.id).get().exists

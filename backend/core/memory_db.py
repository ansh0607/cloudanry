"""In-memory Firestore stub for DEMO_MODE.

Implements exactly the Firestore API surface this project uses:

    db.collection(name).add(doc)                    -> (None, DocRef)
    db.collection(name).document(id).get()/.update()/.delete()
    collection.where(field, "==" | "!=", value).order_by(f, direction=).limit(n).stream()

Data lives only for the lifetime of the server process — perfect for demos,
never a substitute for real Firestore.
"""
import copy
import random
import string
import threading
from typing import Any, Optional

_ID_ALPHABET = string.ascii_letters + string.digits
_lock = threading.Lock()


def _new_id() -> str:
    return "".join(random.choices(_ID_ALPHABET, k=20))


class _Snapshot:
    def __init__(self, doc_id: str, data: Optional[dict[str, Any]]):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> Optional[dict[str, Any]]:
        return copy.deepcopy(self._data) if self._data is not None else None


class _DocRef:
    def __init__(self, store: dict[str, dict[str, Any]], doc_id: str):
        self.id = doc_id
        self._store = store

    def get(self) -> _Snapshot:
        data = self._store.get(self.id)
        return _Snapshot(self.id, copy.deepcopy(data) if data is not None else None)

    def update(self, updates: dict[str, Any]) -> None:
        with _lock:
            current = self._store.setdefault(self.id, {})
            current.update(copy.deepcopy(updates))

    def delete(self) -> None:
        with _lock:
            self._store.pop(self.id, None)


class _Query:
    def __init__(self, docs: dict[str, dict[str, Any]]):
        self._docs = docs
        self._filters: list[tuple[str, str, Any]] = []
        self._order: Optional[tuple[str, str]] = None
        self._limit: Optional[int] = None

    def where(self, field: str, op: str, value: Any) -> "_Query":
        self._filters.append((field, op, value))
        return self

    def order_by(self, field: str, direction: str = "ASCENDING") -> "_Query":
        self._order = (field, direction.upper())
        return self

    def limit(self, n: int) -> "_Query":
        self._limit = n
        return self

    def stream(self) -> list[_Snapshot]:
        with _lock:
            items = [(doc_id, copy.deepcopy(data)) for doc_id, data in self._docs.items()]
        out: list[_Snapshot] = []
        for doc_id, data in items:
            keep = True
            for field, op, value in self._filters:
                actual = (data or {}).get(field)
                if op == "==":
                    keep = actual == value
                elif op == "!=":
                    keep = actual != value
                else:
                    raise ValueError(f"Unsupported demo query op: {op!r}")
                if not keep:
                    break
            if keep:
                out.append(_Snapshot(doc_id, data))
        if self._order:
            field, direction = self._order

            def _key(snap: _Snapshot):
                v = (snap.to_dict() or {}).get(field)
                return (v is None, v)

            out.sort(key=_key, reverse=(direction == "DESCENDING"))
        if self._limit is not None:
            out = out[: self._limit]
        return out


class _Collection:
    def __init__(self, store: dict[str, dict[str, Any]]):
        self._store = store

    def add(self, data: dict[str, Any]) -> tuple[None, _DocRef]:
        doc_id = _new_id()
        with _lock:
            self._store[doc_id] = copy.deepcopy(data)
        return (None, _DocRef(self._store, doc_id))

    def document(self, doc_id: str) -> _DocRef:
        return _DocRef(self._store, doc_id)

    def where(self, field: str, op: str, value: Any) -> _Query:
        return _Query(self._store).where(field, op, value)

    def order_by(self, field: str, direction: str = "ASCENDING") -> _Query:
        return _Query(self._store).order_by(field, direction)

    def limit(self, n: int) -> _Query:
        return _Query(self._store).limit(n)

    def stream(self) -> list[_Snapshot]:
        return _Query(self._store).stream()


class MemoryFirestore:
    def __init__(self) -> None:
        self._collections: dict[str, dict[str, dict[str, Any]]] = {}

    def collection(self, name: str) -> _Collection:
        with _lock:
            if name not in self._collections:
                self._collections[name] = {}
            return _Collection(self._collections[name])

    def clear(self) -> None:
        with _lock:
            self._collections.clear()


_instance: Optional[MemoryFirestore] = None


def get_instance() -> MemoryFirestore:
    global _instance
    if _instance is None:
        with _lock:
            if _instance is None:
                _instance = MemoryFirestore()
    return _instance

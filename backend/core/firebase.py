"""Firestore client singleton. Raises a clear error if credentials are missing."""
import json
import threading
from typing import Any

from backend.core.config import get_settings

_db = None
_lock = threading.Lock()
_init_error: str | None = None


def _initialize():
    global _db, _init_error
    settings = get_settings()
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        cred: Any = None
        if settings.firebase_credentials_json:
            cred = credentials.Certificate(json.loads(settings.firebase_credentials_json))
        elif settings.firebase_credentials_path:
            cred = credentials.Certificate(settings.firebase_credentials_path)

        if firebase_admin._apps:
            app = firebase_admin.get_app()
        else:
            app = firebase_admin.initialize_app(cred)
        _db = firestore.client(app)
    except Exception as e:  # pragma: no cover - depends on env
        _db = None
        _init_error = str(e)


def get_db():
    """Return the Firestore client, or raise a friendly configuration error.

    In DEMO_MODE returns a thread-safe in-memory stub implementing the same
    query surface, so the whole app runs with zero credentials.
    """
    global _init_error
    if get_settings().demo_mode:
        from backend.core.memory_db import get_instance

        return get_instance()
    if _db is None:
        with _lock:
            if _db is None and _init_error is None:
                _initialize()
        if _db is None:
            detail = f" (_init error: {_init_error})" if _init_error else ""
            raise RuntimeError(
                "Firestore is not configured. Set FIREBASE_CREDENTIALS_JSON or "
                f"FIREBASE_CREDENTIALS_PATH in .env (see .env.example).{detail}"
            )
    return _db


def db_available() -> bool:
    return _db is not None

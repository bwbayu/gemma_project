from __future__ import annotations

from datetime import datetime, timezone

from app.repositories.firestore.base import get_collection

APP_STATE_COLLECTION = "app_state"
RUNTIME_DOC_ID = "runtime"


def set_active_workspace_id(workspace_id: str) -> None:
    get_collection(APP_STATE_COLLECTION).document(RUNTIME_DOC_ID).set(
        {
            "active_workspace_id": workspace_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def get_active_workspace_id() -> str | None:
    snapshot = get_collection(APP_STATE_COLLECTION).document(RUNTIME_DOC_ID).get()
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    return data.get("active_workspace_id")

from __future__ import annotations

from google.cloud import firestore

from app.repositories.firestore.base import get_collection

WORKSPACES_COLLECTION = "workspaces"


def create_workspace(workspace_id: str, payload: dict) -> None:
    """Write a new workspace document to Firestore."""
    get_collection(WORKSPACES_COLLECTION).document(workspace_id).set(payload)


def update_workspace(workspace_id: str, payload: dict) -> None:
    """Merge the given fields into an existing workspace document."""
    get_collection(WORKSPACES_COLLECTION).document(workspace_id).set(payload, merge=True)


def get_workspace(workspace_id: str) -> dict | None:
    """Fetch a workspace document by ID, returning None if it does not exist."""
    snapshot = get_collection(WORKSPACES_COLLECTION).document(workspace_id).get()
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    data["workspace_id"] = snapshot.id
    return data


def list_all_workspaces() -> list[dict]:
    """Return every workspace document, with workspace_id injected."""
    docs = get_collection(WORKSPACES_COLLECTION).stream()
    results: list[dict] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["workspace_id"] = doc.id
        results.append(data)
    return results


def find_workspace_by_form_id(form_id: str) -> dict | None:
    """Find the first workspace linked to a given Google Form ID, or None."""
    docs = (
        get_collection(WORKSPACES_COLLECTION)
        .where(filter=firestore.FieldFilter("form_id", "==", form_id))
        .limit(1)
        .stream()
    )
    for doc in docs:
        data = doc.to_dict() or {}
        data["workspace_id"] = doc.id
        return data
    return None

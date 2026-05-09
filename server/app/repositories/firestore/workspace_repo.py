from __future__ import annotations

from google.cloud import firestore

from app.repositories.firestore.base import get_collection

WORKSPACES_COLLECTION = "workspaces"


def create_workspace(workspace_id: str, payload: dict) -> None:
    get_collection(WORKSPACES_COLLECTION).document(workspace_id).set(payload)


def update_workspace(workspace_id: str, payload: dict) -> None:
    get_collection(WORKSPACES_COLLECTION).document(workspace_id).set(payload, merge=True)


def get_workspace(workspace_id: str) -> dict | None:
    snapshot = get_collection(WORKSPACES_COLLECTION).document(workspace_id).get()
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    data["workspace_id"] = snapshot.id
    return data


def find_workspace_by_form_id(form_id: str) -> dict | None:
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

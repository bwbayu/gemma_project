from __future__ import annotations

from google.cloud import firestore

from app.repositories.firestore.base import get_collection

QUESTIONS_COLLECTION = "questions"


def create_question(question_id: str, payload: dict) -> None:
    get_collection(QUESTIONS_COLLECTION).document(question_id).set(payload)


def update_question(question_id: str, payload: dict) -> None:
    get_collection(QUESTIONS_COLLECTION).document(question_id).set(payload, merge=True)


def get_question(question_id: str) -> dict | None:
    snapshot = get_collection(QUESTIONS_COLLECTION).document(question_id).get()
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    data["question_id"] = snapshot.id
    return data


def list_questions_by_workspace(workspace_id: str) -> list[dict]:
    docs = (
        get_collection(QUESTIONS_COLLECTION)
        .where(filter=firestore.FieldFilter("workspace_id", "==", workspace_id))
        .stream()
    )
    items: list[dict] = []
    for doc in docs:
        data = doc.to_dict() or {}
        data["question_id"] = doc.id
        items.append(data)
    items.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return items

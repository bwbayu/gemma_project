from __future__ import annotations

from google.cloud import firestore

from app.repositories.firestore.base import get_collection

JOBS_COLLECTION = "jobs"


def create_job(job_id: str, payload: dict) -> None:
    """Write a new job document to Firestore."""
    get_collection(JOBS_COLLECTION).document(job_id).set(payload)


def update_job(job_id: str, payload: dict) -> None:
    """Merge the given fields into an existing job document."""
    get_collection(JOBS_COLLECTION).document(job_id).set(payload, merge=True)


def get_job(job_id: str) -> dict | None:
    """Fetch a job document by ID, returning None if it does not exist."""
    snapshot = get_collection(JOBS_COLLECTION).document(job_id).get()
    if not snapshot.exists:
        return None
    data = snapshot.to_dict() or {}
    data["job_id"] = snapshot.id
    return data


def get_latest_job_by_question(question_id: str) -> dict | None:
    """Return the most recently created job for a question, or None if no jobs exist."""
    docs = (
        get_collection(JOBS_COLLECTION)
        .where(filter=firestore.FieldFilter("question_id", "==", question_id))
        .stream()
    )
    latest: dict | None = None
    latest_id: str | None = None
    for doc in docs:
        data = doc.to_dict() or {}
        created_at = data.get("created_at", "")
        if latest is None or created_at > latest.get("created_at", ""):
            latest = data
            latest_id = doc.id
    if latest is None or latest_id is None:
        return None
    latest["job_id"] = latest_id
    return latest

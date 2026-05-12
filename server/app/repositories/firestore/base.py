from __future__ import annotations

from google.cloud.firestore import Client

from app.dependencies import get_infra_clients


def get_firestore_client() -> Client:
    """Return the shared Firestore client from the initialized infrastructure clients."""
    return get_infra_clients().firestore_client


def get_collection(name: str):
    """Return a Firestore CollectionReference for the given collection name."""
    return get_firestore_client().collection(name)

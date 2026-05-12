from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.repositories.firestore.app_state_repo import (
    get_active_workspace_id,
    set_active_workspace_id,
)
from app.repositories.firestore.workspace_repo import (
    create_workspace,
    get_workspace,
)
from app.utils.errors import AppError

def _now_iso() -> str:
    """Return the current UTC timestamp as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _build_form_urls(form_id: str) -> tuple[str, str]:
    """Build the Google Form edit and responder URLs from a form ID."""
    edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    responder_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
    return edit_url, responder_url

def _to_workspace_response(entity: dict) -> dict:
    """Reshape a Firestore workspace document into the API response shape."""
    return {
        "workspaceId": entity["workspace_id"],
        "formRef": {
            "formId": entity["form_id"],
            "formTitle": entity["form_title"],
            "formDescription": entity["form_description"],
            "formEditUrl": entity["form_edit_url"],
            "formResponderUrl": entity["form_responder_url"],
        },
        "createdAt": entity["created_at"],
        "updatedAt": entity["updated_at"],
    }


def create_workspace_service(title: str, description: str) -> dict:
    """Create a Google Form, persist the workspace in Firestore, and set it as active."""
    clean_title = title.strip()
    clean_description = description.strip()
    if not clean_title:
        raise AppError(
            code="INVALID_WORKSPACE_TITLE",
            message="Workspace title is required.",
            status_code=422,
        )
    if not clean_description:
        raise AppError(
            code="INVALID_WORKSPACE_DESCRIPTION",
            message="Workspace description is required.",
            status_code=422,
        )

    workspace_id = str(uuid.uuid4())
    # Form ID placeholder in stage 2 until real Forms create/open sync logic.
    from src.tools.form_tools import create_form

    form  = create_form(clean_title, clean_description)

    # form_id = f"mock_form_{uuid.uuid4().hex[:12]}"
    form_id = form["formId"]

    edit_url, responder_url = _build_form_urls(form_id)
    now = _now_iso()
    payload = {
        "form_id": form_id,
        "form_title": clean_title,
        "form_description": clean_description,
        "form_edit_url": edit_url,
        "form_responder_url": responder_url,
        "status": "active",
        "created_at": now,
        "updated_at": now,
    }
    create_workspace(workspace_id, payload)
    set_active_workspace_id(workspace_id)

    payload["workspace_id"] = workspace_id
    return _to_workspace_response(payload)


def get_active_workspace_service() -> dict | None:
    """Look up the active workspace ID from app state and return the workspace document, or None."""
    workspace_id = get_active_workspace_id()
    if not workspace_id:
        return None
    entity = get_workspace(workspace_id)
    if not entity:
        return None
    return _to_workspace_response(entity)


def get_workspace_links_service(workspace_id: str) -> dict:
    """Return the form edit and responder URLs for a workspace, raising 404 if not found."""
    entity = get_workspace(workspace_id)
    if not entity:
        raise AppError(
            code="WORKSPACE_NOT_FOUND",
            message="Workspace not found.",
            details={"workspaceId": workspace_id},
            status_code=404,
        )
    return {
        "workspaceId": entity["workspace_id"],
        "formEditUrl": entity["form_edit_url"],
        "formResponderUrl": entity["form_responder_url"],
    }

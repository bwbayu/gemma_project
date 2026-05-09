from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from app.repositories.firestore.app_state_repo import (
    get_active_workspace_id,
    set_active_workspace_id,
)
from app.repositories.firestore.workspace_repo import (
    create_workspace,
    find_workspace_by_form_id,
    get_workspace,
)
from app.utils.errors import AppError

FORM_URL_PATTERN = re.compile(
    r"^https?://docs\.google\.com/forms/d/([a-zA-Z0-9_-]{20,})(?:/|$)",
    re.IGNORECASE,
)
FORM_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{20,}$")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_form_urls(form_id: str) -> tuple[str, str]:
    edit_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    responder_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
    return edit_url, responder_url


def _normalize_form_ref(form_ref: str) -> str:
    trimmed = form_ref.strip()
    if not trimmed:
        raise AppError(
            code="INVALID_FORM_REF",
            message="Form reference cannot be empty.",
            status_code=422,
        )

    url_match = FORM_URL_PATTERN.match(trimmed)
    if url_match:
        return url_match.group(1)
    if FORM_ID_PATTERN.match(trimmed):
        return trimmed
    raise AppError(
        code="INVALID_FORM_REF",
        message="Form reference must be a valid Google Form URL or Form ID.",
        details={"formRef": form_ref},
        status_code=422,
    )


def _to_workspace_response(entity: dict) -> dict:
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


def open_workspace_service(form_ref: str) -> dict:
    form_id = _normalize_form_ref(form_ref)
    existing = find_workspace_by_form_id(form_id)
    if existing:
        set_active_workspace_id(existing["workspace_id"])
        return _to_workspace_response(existing)

    workspace_id = str(uuid.uuid4())
    edit_url, responder_url = _build_form_urls(form_id)
    now = _now_iso()
    payload = {
        "form_id": form_id,
        "form_title": "Imported Form Workspace",
        "form_description": f"Imported from form reference: {form_ref.strip()}",
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
    workspace_id = get_active_workspace_id()
    if not workspace_id:
        return None
    entity = get_workspace(workspace_id)
    if not entity:
        return None
    return _to_workspace_response(entity)


def get_workspace_links_service(workspace_id: str) -> dict:
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

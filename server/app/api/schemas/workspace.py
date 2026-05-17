"""Schemas describing a workspace and the Google Form it wraps."""

from __future__ import annotations

from pydantic import BaseModel, Field


class _ApiModel(BaseModel):
    """Base model that lets handlers populate fields by either snake_case or camelCase alias."""

    model_config = {
        "populate_by_name": True,
    }


class WorkspaceFormRefModel(_ApiModel):
    """Reference to the Google Form a workspace is backed by (IDs + share URLs)."""

    form_id: str = Field(alias="formId")
    form_title: str = Field(alias="formTitle")
    form_description: str = Field(alias="formDescription")
    form_edit_url: str = Field(alias="formEditUrl")
    form_responder_url: str = Field(alias="formResponderUrl")


class WorkspaceModel(_ApiModel):
    """One workspace: an ID + its Form reference + timestamps."""

    workspace_id: str = Field(alias="workspaceId")
    form_ref: WorkspaceFormRefModel = Field(alias="formRef")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class CreateWorkspaceRequest(_ApiModel):
    """Request body for creating a workspace (title + description used for the Google Form)."""

    title: str
    description: str


class WorkspaceLinksResponse(_ApiModel):
    """Minimal payload returned by the `/links` endpoint for share/preview UIs."""

    workspace_id: str = Field(alias="workspaceId")
    form_edit_url: str = Field(alias="formEditUrl")
    form_responder_url: str = Field(alias="formResponderUrl")

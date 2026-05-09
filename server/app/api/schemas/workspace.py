from __future__ import annotations

from pydantic import BaseModel, Field


class _ApiModel(BaseModel):
    model_config = {
        "populate_by_name": True,
    }


class WorkspaceFormRefModel(_ApiModel):
    form_id: str = Field(alias="formId")
    form_title: str = Field(alias="formTitle")
    form_description: str = Field(alias="formDescription")
    form_edit_url: str = Field(alias="formEditUrl")
    form_responder_url: str = Field(alias="formResponderUrl")


class WorkspaceModel(_ApiModel):
    workspace_id: str = Field(alias="workspaceId")
    form_ref: WorkspaceFormRefModel = Field(alias="formRef")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class CreateWorkspaceRequest(_ApiModel):
    title: str
    description: str


class WorkspaceLinksResponse(_ApiModel):
    workspace_id: str = Field(alias="workspaceId")
    form_edit_url: str = Field(alias="formEditUrl")
    form_responder_url: str = Field(alias="formResponderUrl")

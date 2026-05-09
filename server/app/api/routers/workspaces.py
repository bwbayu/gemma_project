from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.schemas.workspace import (
    CreateWorkspaceRequest,
    OpenWorkspaceRequest,
    WorkspaceLinksResponse,
    WorkspaceModel,
)
from app.services.workspace_service import (
    create_workspace_service,
    get_active_workspace_service,
    get_workspace_links_service,
    open_workspace_service,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/active", response_model=WorkspaceModel | None)
def get_active_workspace():
    workspace = get_active_workspace_service()
    if workspace is None:
        return JSONResponse(status_code=status.HTTP_200_OK, content=None)
    return workspace


@router.post("", response_model=WorkspaceModel, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: CreateWorkspaceRequest):
    return create_workspace_service(payload.title, payload.description)


@router.post("/open", response_model=WorkspaceModel)
def open_workspace(payload: OpenWorkspaceRequest):
    return open_workspace_service(payload.form_ref)


@router.get("/{workspace_id}/links", response_model=WorkspaceLinksResponse)
def get_workspace_links(workspace_id: str):
    return get_workspace_links_service(workspace_id)

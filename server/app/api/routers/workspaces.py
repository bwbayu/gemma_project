from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.api.schemas.workspace import (
    CreateWorkspaceRequest,
    WorkspaceLinksResponse,
    WorkspaceModel,
)
from app.services.workspace_service import (
    create_workspace_service,
    get_active_workspace_service,
    get_workspace_links_service,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/active", response_model=WorkspaceModel | None)
def get_active_workspace():
    """Return the currently active workspace, or null if none has been set."""
    workspace = get_active_workspace_service()
    if workspace is None:
        return JSONResponse(status_code=status.HTTP_200_OK, content=None)
    return workspace


@router.post("", response_model=WorkspaceModel, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: CreateWorkspaceRequest):
    """Create a new Google Form-backed workspace and set it as the active workspace."""
    return create_workspace_service(payload.title, payload.description)


@router.get("/{workspace_id}/links", response_model=WorkspaceLinksResponse)
def get_workspace_links(workspace_id: str):
    """Return the edit and responder URLs for the Google Form associated with a workspace."""
    return get_workspace_links_service(workspace_id)

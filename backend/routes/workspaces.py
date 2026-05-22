from fastapi import APIRouter, HTTPException, Depends
from backend.models.collaboration_schema import (
    WorkspaceCreate, WorkspaceOut, WorkspaceMemberCreate, WorkspaceMemberOut
)
from backend.services.workspace_services import (
    create_workspace, get_workspaces, get_workspace, add_member, get_members
)

router = APIRouter()

# In a real app, Depends(get_current_user) would be used.
# For simplicity, using a mock string or reading from request headers.

@router.post("/", response_model=WorkspaceOut)
def api_create_workspace(workspace: WorkspaceCreate):
    # Mocking user_id
    user_id = "mock_user_123"
    return create_workspace(workspace.name, user_id)

@router.get("/", response_model=list[WorkspaceOut])
def api_get_workspaces():
    return get_workspaces()

@router.get("/{workspace_id}", response_model=WorkspaceOut)
def api_get_workspace(workspace_id: str):
    workspace = get_workspace(workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace

@router.post("/{workspace_id}/members", response_model=WorkspaceMemberOut)
def api_add_member(workspace_id: str, member: WorkspaceMemberCreate):
    return add_member(workspace_id, member.user_id, member.role)

@router.get("/{workspace_id}/members", response_model=list[WorkspaceMemberOut])
def api_get_members(workspace_id: str):
    return get_members(workspace_id)

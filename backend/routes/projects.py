from fastapi import APIRouter, HTTPException
from backend.models.collaboration_schema import ProjectCreate, ProjectOut
from backend.services.project_services import create_project, get_projects, get_project

router = APIRouter()

@router.post("/", response_model=ProjectOut)
def api_create_project(project: ProjectCreate):
    user_id = "mock_user_123"
    return create_project(project.workspace_id, project.name, project.description, user_id)

@router.get("/", response_model=list[ProjectOut])
def api_get_projects(workspace_id: str = None):
    return get_projects(workspace_id)

@router.get("/{project_id}", response_model=ProjectOut)
def api_get_project(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

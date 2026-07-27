import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AuditLog, Command, FileOperation, Project
from app.schemas import ProjectCreate, ProjectUpdate
from app.services.files import WorkspaceService
from app.services.planner import PlannerError, get_planner

router = APIRouter()


def render(request: Request, template: str, **context):
    return request.app.state.templates.TemplateResponse(request=request, name=template, context=context)


def project_or_404(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    projects = db.scalars(select(Project).order_by(Project.updated_at.desc())).all()
    return render(request, "dashboard.html", projects=projects)


@router.post("/projects")
def create_project(name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    data = ProjectCreate(name=name, description=description)
    project = Project(**data.model_dump())
    db.add(project); db.flush()
    db.add(AuditLog(project_id=project.id, event="project.created", details=project.name)); db.commit()
    return RedirectResponse(f"/projects/{project.id}", status_code=303)


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def view_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    return render(request, "project.html", project=project_or_404(db, project_id))


@router.post("/projects/{project_id}/edit")
def edit_project(project_id: int, name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    project = project_or_404(db, project_id); data = ProjectUpdate(name=name, description=description)
    project.name, project.description = data.name, data.description
    db.add(AuditLog(project_id=project.id, event="project.updated", details=project.name)); db.commit()
    return RedirectResponse(f"/projects/{project.id}", status_code=303)


@router.post("/projects/{project_id}/archive")
def archive_project(project_id: int, db: Session = Depends(get_db)):
    project = project_or_404(db, project_id); project.archived = True
    db.add(AuditLog(project_id=project.id, event="project.archived", details=project.name)); db.commit()
    return RedirectResponse("/", status_code=303)


@router.post("/projects/{project_id}/commands")
def propose(project_id: int, instruction: str = Form(...), db: Session = Depends(get_db)):
    project = project_or_404(db, project_id)
    if project.archived:
        raise HTTPException(409, "Archived projects cannot accept commands")
    settings = get_settings()
    planner = get_planner(settings.openai_api_key, settings.openai_model, settings.openai_timeout_seconds)
    try:
        plan = planner.create_plan(instruction)
    except PlannerError as exc:
        raise HTTPException(502, str(exc)) from exc
    payload = {"title": plan.title, "summary": plan.summary, "steps": plan.steps}
    command = Command(project_id=project_id, instruction=instruction.strip(), plan_json=json.dumps(payload, ensure_ascii=False))
    db.add(command); db.flush()
    for op in plan.operations:
        db.add(FileOperation(command_id=command.id, operation=op.operation, relative_path=op.path, content=op.content))
    db.add(AuditLog(project_id=project_id, command_id=command.id, event="command.proposed", details=plan.summary)); db.commit()
    return RedirectResponse(f"/commands/{command.id}", status_code=303)


@router.get("/commands/{command_id}", response_class=HTMLResponse)
def command_page(command_id: int, request: Request, db: Session = Depends(get_db)):
    command = db.get(Command, command_id)
    if command is None: raise HTTPException(404, "Command not found")
    return render(request, "command.html", command=command, plan=json.loads(command.plan_json))


@router.post("/commands/{command_id}/decision")
def decide(command_id: int, decision: str = Form(...), db: Session = Depends(get_db)):
    command = db.get(Command, command_id)
    if command is None: raise HTTPException(404, "Command not found")
    if command.status != "pending_approval": raise HTTPException(409, "Command has already been decided")
    if decision not in {"approve", "reject"}: raise HTTPException(400, "Invalid decision")
    command.approved = decision == "approve"; command.decided_at = datetime.now(timezone.utc)
    if decision == "reject":
        command.status = "rejected"
        for op in command.operations: op.status = "rejected"
    else:
        service = WorkspaceService(get_settings().workspace_root)
        try:
            for op in command.operations:
                if op.operation != "write": raise ValueError("Unsupported file operation")
                service.write(command.project_id, op.relative_path, op.content); op.status = "completed"
            command.status = "completed"
        except Exception as exc:
            command.status = "failed"; command.error_message = str(exc)
            for op in command.operations:
                if op.status != "completed": op.status, op.error_message = "failed", str(exc)
    db.add(AuditLog(project_id=command.project_id, command_id=command.id, event=f"command.{command.status}", details=decision)); db.commit()
    return RedirectResponse(f"/commands/{command.id}", status_code=303)


@router.get("/activity", response_class=HTMLResponse)
def activity(request: Request, db: Session = Depends(get_db)):
    logs = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(250)).all()
    return render(request, "activity.html", logs=logs)

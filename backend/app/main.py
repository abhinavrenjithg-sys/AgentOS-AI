from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .core import settings
from .db import SessionLocal, get_db
from .engine import execute_run
from .models import Artifact, StepRun, Workflow, WorkflowRun
from .planner import make_plan, validate_plan
from .schemas import Plan, PlanRequest, RunOut, WorkflowOut

app = FastAPI(
    title="AgentOS AI",
    version="0.1.0",
    description="Bounded, approval-gated public research workflows",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
def health():
    llm_configured = bool(
        settings.openai_base_url and settings.openai_api_key and settings.openai_model
    )
    return {
        "status": "ok",
        "mode": "development",
        "planner": "openai_compatible" if llm_configured else "deterministic",
        "reader": "bounded_http",
        "browser_session_available": False,
    }


@app.post("/api/v1/plans", response_model=Plan)
def plan(req: PlanRequest):
    try:
        return make_plan(req.task, req.source_urls)
    except ValueError as exc:
        raise HTTPException(422, str(exc))


@app.post("/api/v1/workflows", response_model=WorkflowOut)
def save_workflow(plan: Plan, db: Session = Depends(get_db)):
    try:
        validate_plan(plan)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    workflow = Workflow(
        name=plan.goal[:72].strip(), goal=plan.goal, definition=plan.model_dump(), version=1
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@app.get("/api/v1/workflows", response_model=list[WorkflowOut])
def workflows(db: Session = Depends(get_db)):
    return db.query(Workflow).order_by(Workflow.created_at.desc()).limit(100).all()


@app.post("/api/v1/workflows/{workflow_id}/runs", response_model=RunOut)
def start_run(workflow_id: int, background: BackgroundTasks, db: Session = Depends(get_db)):
    workflow = db.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    run = WorkflowRun(workflow_id=workflow.id, status="pending", approved=True)
    db.add(run)
    db.flush()
    for item in workflow.definition["steps"]:
        db.add(StepRun(run_id=run.id, key=item["id"], title=item["title"], tool=item["tool"]))
    db.commit()
    db.refresh(run)
    background.add_task(_execute_in_session, run.id)
    return run


def _execute_in_session(run_id):
    with SessionLocal() as db:
        execute_run(db, run_id)


@app.get("/api/v1/runs", response_model=list[RunOut])
def runs(db: Session = Depends(get_db)):
    return db.query(WorkflowRun).order_by(WorkflowRun.created_at.desc()).limit(100).all()


@app.get("/api/v1/runs/{run_id}", response_model=RunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    item = db.get(WorkflowRun, run_id)
    if not item:
        raise HTTPException(404, "Execution not found")
    return item


@app.get("/api/v1/artifacts/{artifact_id}/download")
def download(artifact_id: int, db: Session = Depends(get_db)):
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(404, "Artifact not found")
    path = Path(artifact.path).resolve()
    root = Path(settings.artifact_dir).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(404, "Artifact file not found")
    return FileResponse(path, media_type=artifact.content_type, filename=artifact.filename)

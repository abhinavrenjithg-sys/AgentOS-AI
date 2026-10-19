from pathlib import Path
import csv
from app.planner import make_plan, validate_plan
from app.schemas import Plan, Step
from app.security import URLPolicyError, check_public_url
from app.db import Base, engine, SessionLocal
from app.models import Workflow, WorkflowRun, StepRun
from app.engine import execute_run
import pytest
from fastapi.testclient import TestClient

def test_planner_builds_bounded_workflow():
    p=make_plan("Research public product pages and make a CSV report",["https://example.com"])
    assert [s.tool for s in p.steps]==["research_public_pages","generate_csv","prepare_email_draft"]
    assert p.source_urls==["https://example.com"]

def test_unknown_tool_is_rejected():
    with pytest.raises(Exception):
        Step(id="bad",title="Bad",tool="shell",description="run arbitrary code")

def test_cycle_is_rejected():
    p=Plan(goal="x",steps=[Step(id="a",title="a",tool="generate_csv",description="",depends_on=["b"]),Step(id="b",title="b",tool="prepare_email_draft",description="",depends_on=["a"])])
    with pytest.raises(ValueError,match="cycle"): validate_plan(p)

@pytest.mark.asyncio
async def test_private_addresses_are_rejected():
    with pytest.raises(URLPolicyError): await check_public_url("http://127.0.0.1/admin")
    with pytest.raises(URLPolicyError): await check_public_url("http://localhost/")

def test_approval_gate_and_step_persistence(tmp_path,monkeypatch):
    import app.engine as engine_module
    monkeypatch.setattr(engine_module.settings,"artifact_dir",str(tmp_path))
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        wf=Workflow(name="demo",goal="demo",definition=make_plan("research test",["https://example.com"]).model_dump());db.add(wf);db.flush()
        run=WorkflowRun(workflow_id=wf.id,approved=False,status="pending");db.add(run);db.flush()
        db.add_all([StepRun(run_id=run.id,key=s["id"],title=s["title"],tool=s["tool"]) for s in wf.definition["steps"]]);db.commit()
        execute_run(db,run.id);assert db.get(WorkflowRun,run.id).status=="pending"

def test_plan_approve_execute_and_download_csv(monkeypatch,tmp_path):
    import app.engine as engine_module
    from app.main import app
    monkeypatch.setattr(engine_module.settings,"artifact_dir",str(tmp_path))
    monkeypatch.setattr(engine_module,"_run_fetch",lambda url:(url,"<html><title>Sample Product</title><meta name='description' content='Price $19'></html>"))
    client=TestClient(app)
    p=client.post("/api/v1/plans",json={"task":"Research this product and create a CSV","source_urls":["https://example.com/product"]})
    assert p.status_code==200
    w=client.post("/api/v1/workflows",json=p.json());assert w.status_code==200
    run=client.post(f"/api/v1/workflows/{w.json()['id']}/runs")
    assert run.status_code==200
    run=client.get(f"/api/v1/runs/{run.json()['id']}");assert run.json()["status"]=="completed"
    result=run.json()["result"]
    assert result["record_count"]==1 and result["email_sent"] is False
    csv_response=client.get(f"/api/v1/artifacts/{result['artifact_id']}/download")
    assert csv_response.status_code==200
    assert "Sample Product" in csv_response.text and "https://example.com/product" in csv_response.text

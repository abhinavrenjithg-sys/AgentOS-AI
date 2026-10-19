from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.planner import make_llm_plan, make_plan, validate_plan
from app.schemas import Plan, Step
from app.security import URLPolicyError, check_public_url


def _test_sessions():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_planner_builds_bounded_workflow():
    plan = make_plan("Research public product pages and make a CSV report", ["https://example.com"])
    assert [step.tool for step in plan.steps] == [
        "research_public_pages",
        "generate_csv",
        "prepare_email_draft",
    ]
    assert plan.source_urls == ["https://example.com"]


def test_unknown_tool_is_rejected():
    with pytest.raises(Exception):
        Step(id="bad", title="Bad", tool="shell", description="run arbitrary code")


def test_cycle_is_rejected():
    plan = Plan(
        goal="Test a workflow cycle",
        steps=[
            Step(
                id="a",
                title="a",
                tool="generate_csv",
                description="Generate output.",
                depends_on=["b"],
            ),
            Step(
                id="b",
                title="b",
                tool="prepare_email_draft",
                description="Prepare a draft.",
                depends_on=["a"],
            ),
        ],
    )
    with pytest.raises(ValueError, match="cycle"):
        validate_plan(plan)


def test_research_urls_must_match_the_approved_plan():
    plan = make_plan("Research this source", ["https://example.com"])
    plan.steps[0].inputs["source_urls"] = ["https://attacker.example"]
    with pytest.raises(ValueError, match="match"):
        validate_plan(plan)


def test_llm_planner_cannot_invent_a_source_url(monkeypatch):
    import app.planner as planner_module

    plan = make_plan("Research this product page", ["https://example.com"])
    plan.mode = "llm"

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": plan.model_dump_json()}}]}

    monkeypatch.setattr(planner_module.settings, "openai_base_url", "https://provider.example/v1")
    monkeypatch.setattr(planner_module.settings, "openai_api_key", "test-key")
    monkeypatch.setattr(planner_module.settings, "openai_model", "test-model")
    monkeypatch.setattr(planner_module.httpx, "post", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(ValueError, match="introduced a URL"):
        make_llm_plan("Research this product page", [])


@pytest.mark.asyncio
async def test_private_addresses_are_rejected():
    with pytest.raises(URLPolicyError):
        await check_public_url("http://127.0.0.1/admin")
    with pytest.raises(URLPolicyError):
        await check_public_url("http://localhost/")


def test_formula_cells_are_neutralized_after_whitespace():
    from app.engine import _safe_cell

    assert _safe_cell("=1+1").startswith("'")
    assert _safe_cell("  =1+1").startswith("'")
    assert _safe_cell("normal text") == "normal text"


def test_approval_gate_and_step_persistence(tmp_path, monkeypatch):
    import app.engine as engine_module
    from app.engine import execute_run
    from app.models import StepRun, Workflow, WorkflowRun

    sessions = _test_sessions()
    monkeypatch.setattr(engine_module.settings, "artifact_dir", str(tmp_path))
    with sessions() as db:
        workflow = Workflow(
            name="demo",
            goal="demo",
            definition=make_plan("research test", ["https://example.com"]).model_dump(),
        )
        db.add(workflow)
        db.flush()
        run = WorkflowRun(workflow_id=workflow.id, approved=False, status="pending")
        db.add(run)
        db.flush()
        db.add_all(
            [
                StepRun(run_id=run.id, key=step["id"], title=step["title"], tool=step["tool"])
                for step in workflow.definition["steps"]
            ]
        )
        db.commit()
        execute_run(db, run.id)
        assert db.get(WorkflowRun, run.id).status == "pending"


def test_plan_approve_execute_and_download_csv(monkeypatch, tmp_path):
    import app.engine as engine_module
    import app.main as main_module

    sessions = _test_sessions()
    monkeypatch.setattr(engine_module.settings, "artifact_dir", str(tmp_path))
    monkeypatch.setattr(main_module, "SessionLocal", sessions)
    monkeypatch.setattr(
        engine_module,
        "_run_fetch",
        lambda url: (
            url,
            "<html><title>Sample Product</title><meta name='description' content='Price $19'></html>",
        ),
    )

    def override_get_db():
        with sessions() as db:
            yield db

    main_module.app.dependency_overrides[main_module.get_db] = override_get_db
    try:
        client = TestClient(main_module.app)
        response = client.post(
            "/api/v1/plans",
            json={
                "task": "Research this product and create a CSV",
                "source_urls": ["https://example.com/product"],
            },
        )
        assert response.status_code == 200
        workflow = client.post("/api/v1/workflows", json=response.json())
        assert workflow.status_code == 200
        run_response = client.post(f"/api/v1/workflows/{workflow.json()['id']}/runs")
        assert run_response.status_code == 200
        run = client.get(f"/api/v1/runs/{run_response.json()['id']}").json()
        assert run["status"] == "completed"
        result = run["result"]
        assert result["record_count"] == 1
        assert result["failed_count"] == 0
        assert result["email_sent"] is False
        from app.models import Artifact

        with sessions() as db:
            saved_artifact = db.get(Artifact, result["artifact_id"])
            assert saved_artifact.data is not None
            Path(saved_artifact.path).unlink()
        csv_response = client.get(f"/api/v1/artifacts/{result['artifact_id']}/download")
        assert csv_response.status_code == 200
        assert "Sample Product" in csv_response.text
        assert "https://example.com/product" in csv_response.text
    finally:
        main_module.app.dependency_overrides.clear()

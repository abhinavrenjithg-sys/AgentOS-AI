import asyncio
import csv
import io
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from .core import settings
from .models import Artifact, StepRun, Workflow, WorkflowRun, now
from .security import fetch_public


def _safe_cell(value: object) -> str:
    text = str(value or "")
    # Spreadsheet applications may evaluate formulas after leading whitespace.
    if text.lstrip(" \t\r\n")[:1] in {"=", "+", "-", "@"}:
        return "'" + text
    return text


def execute_run(db: Session, run_id: int) -> None:
    run = db.get(WorkflowRun, run_id)
    if not run or not run.approved or run.status != "pending":
        return

    workflow = db.get(Workflow, run.workflow_id)
    if not workflow:
        run.status = "failed"
        run.error = "Workflow not found"
        run.finished_at = now()
        db.commit()
        return

    run.status = "running"
    run.started_at = now()
    db.commit()
    records: list[dict[str, str]] = []

    try:
        for item in workflow.definition["steps"]:
            step = db.query(StepRun).filter_by(run_id=run.id, key=item["id"]).one()
            step.status = "running"
            step.started_at = now()
            db.commit()

            if item["tool"] == "research_public_pages":
                urls = workflow.definition.get("source_urls", [])
                if not urls:
                    raise ValueError("Add at least one public source URL to run research.")
                for url in urls:
                    retrieved_at = datetime.now(timezone.utc).isoformat()
                    try:
                        final_url, html = _run_fetch(url)
                        soup = BeautifulSoup(html, "html.parser")
                        title = soup.title.get_text(" ", strip=True) if soup.title else ""
                        meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
                            "meta", attrs={"property": "og:description"}
                        )
                        description = meta.get("content", "").strip() if meta else ""
                        evidence = " ".join(soup.stripped_strings)
                        records.append(
                            {
                                "source_url": final_url[:2048],
                                "title": title[:200],
                                "description": description[:500],
                                "evidence": evidence[:500],
                                "retrieved_at": retrieved_at,
                                "error": "",
                            }
                        )
                    except Exception as exc:
                        records.append(
                            {
                                "source_url": url[:2048],
                                "title": "",
                                "description": "",
                                "evidence": "",
                                "retrieved_at": retrieved_at,
                                "error": str(exc)[:400],
                            }
                        )
                successful = [record for record in records if not record["error"]]
                if not successful:
                    raise RuntimeError("No source could be researched successfully.")
                step.output = {
                    "records": records,
                    "reader": "bounded_http",
                    "browser_session": False,
                }

            elif item["tool"] == "generate_csv":
                fields = ["source_url", "title", "description", "evidence", "retrieved_at", "error"]
                buffer = io.StringIO(newline="")
                writer = csv.DictWriter(buffer, fieldnames=fields)
                writer.writeheader()
                writer.writerows(
                    {key: _safe_cell(record.get(key, "")) for key in fields} for record in records
                )

                filename = f"research-run-{run.id}.csv"
                path = Path(settings.artifact_dir) / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(buffer.getvalue(), encoding="utf-8-sig")
                artifact = Artifact(
                    run_id=run.id,
                    filename=filename,
                    path=str(path.resolve()),
                    content_type="text/csv",
                )
                db.add(artifact)
                db.flush()
                step.output = {
                    "artifact_id": artifact.id,
                    "filename": filename,
                    "rows": len(records),
                }

            elif item["tool"] == "prepare_email_draft":
                successful_count = sum(not record["error"] for record in records)
                step.output = {
                    "subject": f"Research summary: {workflow.name}",
                    "body": f"Research complete. {successful_count} successful source record(s) are included in the attached CSV. Please review findings and the artifact before sending.",
                    "sent": False,
                }
            else:
                raise ValueError("Unsupported registered tool")

            step.status = "completed"
            step.finished_at = now()
            db.commit()

        successful_count = sum(not record["error"] for record in records)
        run.result = {
            "record_count": successful_count,
            "source_count": len(records),
            "failed_count": len(records) - successful_count,
            "artifact_id": next(
                (
                    s.output.get("artifact_id")
                    for s in run.steps
                    if s.output and s.output.get("artifact_id")
                ),
                None,
            ),
            "email_sent": False,
            "reader": "bounded_http",
            "records": records,
        }
        run.status = "completed"
        run.finished_at = now()
        db.commit()
    except Exception as exc:
        db.rollback()
        run = db.get(WorkflowRun, run_id)
        run.status = "failed"
        run.error = str(exc)[:1000]
        run.finished_at = now()
        active = db.query(StepRun).filter_by(run_id=run_id, status="running").first()
        if active:
            active.status = "failed"
            active.error = run.error
            active.finished_at = now()
        db.commit()


def _run_fetch(url: str) -> tuple[str, str]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(fetch_public(url))
    raise RuntimeError("Research adapter cannot run inside active event loop")

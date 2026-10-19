import csv, io, re
from datetime import datetime, timezone
from pathlib import Path
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from .core import settings
from .models import Workflow, WorkflowRun, StepRun, Artifact, now
from .security import fetch_public

def execute_run(db: Session, run_id: int):
    run = db.get(WorkflowRun, run_id)
    if not run or not run.approved or run.status != "pending": return
    workflow = db.get(Workflow, run.workflow_id)
    run.status="running"; run.started_at=now(); db.commit()
    records=[]
    try:
        for item in workflow.definition["steps"]:
            step = db.query(StepRun).filter_by(run_id=run.id,key=item["id"]).one()
            step.status="running"; step.started_at=now(); db.commit()
            if item["tool"] == "research_public_pages":
                urls=workflow.definition.get("source_urls", [])
                if not urls: raise ValueError("Add at least one public source URL to run research.")
                for url in urls:
                    try:
                        final_url, html = _run_fetch(url)
                        soup=BeautifulSoup(html,"html.parser")
                        title=soup.title.get_text(" ",strip=True) if soup.title else ""
                        meta=soup.find("meta",attrs={"name":"description"}) or soup.find("meta",attrs={"property":"og:description"})
                        desc=meta.get("content","").strip() if meta else ""
                        text=" ".join(soup.stripped_strings)
                        records.append({"source_url":final_url,"title":title,"description":desc,"evidence":text[:500],"retrieved_at":datetime.now(timezone.utc).isoformat()})
                    except Exception as exc: records.append({"source_url":url,"title":"","description":"","evidence":"","retrieved_at":datetime.now(timezone.utc).isoformat(),"error":str(exc)[:400]})
                if not records or all(r.get("error") for r in records): raise RuntimeError("No source could be researched successfully.")
                step.output={"records":records,"reader":"bounded_http","browser_session":False}
            elif item["tool"] == "generate_csv":
                fields=["source_url","title","description","evidence","retrieved_at"]
                def safe_cell(value):
                    text=str(value or "")
                    return "'"+text if text.startswith(("=","+","-","@","\t","\r")) else text
                buf=io.StringIO(newline=""); writer=csv.DictWriter(buf,fieldnames=fields); writer.writeheader(); writer.writerows([{k:safe_cell(r.get(k,"")) for k in fields} for r in records])
                filename=f"research-run-{run.id}.csv"; path=Path(settings.artifact_dir)/filename; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(buf.getvalue(),encoding="utf-8-sig")
                artifact=Artifact(run_id=run.id,filename=filename,path=str(path.resolve()),content_type="text/csv"); db.add(artifact); db.flush()
                step.output={"artifact_id":artifact.id,"filename":filename,"rows":len(records)}
            elif item["tool"] == "prepare_email_draft":
                step.output={"subject":f"Research summary: {workflow.name}","body":f"Research complete. {len(records)} source record(s) are included in the attached CSV. Please review findings and the artifact before sending.","sent":False}
            else: raise ValueError("Unsupported registered tool")
            step.status="completed"; step.finished_at=now(); db.commit()
        run.result={"record_count":len(records),"artifact_id":next((s.output.get("artifact_id") for s in run.steps if s.output and s.output.get("artifact_id")),None),"email_sent":False,"reader":"bounded_http","records":records}
        run.status="completed"; run.finished_at=now(); db.commit()
    except Exception as exc:
        db.rollback(); run=db.get(WorkflowRun,run_id); run.status="failed"; run.error=str(exc)[:1000]; run.finished_at=now()
        active=db.query(StepRun).filter_by(run_id=run_id,status="running").first()
        if active: active.status="failed"; active.error=run.error; active.finished_at=now()
        db.commit()

def _run_fetch(url):
    import asyncio
    try: asyncio.get_running_loop()
    except RuntimeError: return asyncio.run(fetch_public(url))
    raise RuntimeError("Research adapter cannot run inside active event loop")

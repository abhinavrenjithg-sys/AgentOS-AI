# API guide

Base path: `/api/v1`. Interactive OpenAPI docs: `/docs`.

- `GET /health`: runtime mode and adapter availability.
- `POST /plans`: `{ "task": "...", "source_urls": ["https://..."] }` → validated plan.
- `POST /workflows`: save a validated plan as version 1.
- `GET /workflows`: recent workflows.
- `POST /workflows/{id}/runs`: explicitly start an approved plan.
- `GET /runs`: recent executions.
- `GET /runs/{id}`: execution and step progress.
- `GET /artifacts/{id}/download`: CSV download.

Authentication is not implemented in the local development mode. Do not publish the API publicly.

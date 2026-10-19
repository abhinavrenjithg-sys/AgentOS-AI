# Architecture

AgentOS is a modular monolith: React/Vite frontend, FastAPI API, SQLAlchemy persistence, and a bounded execution engine. The API persists workflow definitions, runs, step state, outputs, and artifact metadata. SQLite is the local default; PostgreSQL is supported through `DATABASE_URL`.

Planning accepts natural language and supplied public URLs. The deterministic planner emits a fixed, validated research → CSV → local email draft workflow. When all `OPENAI_*` settings are configured, an OpenAI-compatible planner may propose a plan; the result is validated against Pydantic, registered tool names, step count, dependency order, and supplied URLs. Model output is never executed as code.

The user reviews the plan before invoking the run endpoint. Runs persist each state transition. The first execution adapter reads bounded HTTP page content and extracts title, description, and a short evidence snippet. It does not claim to launch a browser. CSV is generated from records and the final draft stays local. The API reports status through polling.

The MVP runs tasks in FastAPI's in-process background task facility. State is durable after a step commit, but process restart interrupts the active run; no automatic resume is currently implemented. Before production, move execution into a durable worker, add leases/idempotency, and implement recovery.

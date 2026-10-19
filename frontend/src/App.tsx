import { useEffect, useState } from "react";
import {
  Activity,
  ArrowDown,
  ArrowRight,
  BadgeCheck,
  Bot,
  Check,
  ChevronDown,
  CircleHelp,
  Clock3,
  Download,
  FileText,
  Globe2,
  LayoutDashboard,
  ListChecks,
  LockKeyhole,
  Menu,
  Plus,
  Settings2,
  Shield,
  Sparkles,
  Workflow as WorkflowIcon,
  X,
} from "lucide-react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const API =
  import.meta.env.VITE_API_BASE ||
  (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "");
const hostedStaticPreview = !import.meta.env.DEV && !API;
const workspaceLabel = import.meta.env.DEV ? "Local workspace" : "Demo workspace";
const environmentLabel = import.meta.env.DEV ? "Development mode" : "Hosted demo";
type Step = {
  id: string;
  title: string;
  tool: string;
  description: string;
  inputs: Record<string, unknown>;
  depends_on: string[];
  approval_required: boolean;
};
type Plan = {
  goal: string;
  steps: Step[];
  risks: string[];
  source_urls: string[];
  mode: string;
};
type Workflow = {
  id: number;
  name: string;
  goal: string;
  version: number;
  definition: Plan;
  created_at: string;
};
type Run = {
  id: number;
  workflow_id: number;
  status: string;
  approved: boolean;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  result?: {
    record_count: number;
    artifact_id: number | null;
    email_sent: boolean;
    reader: string;
    records: Record<string, string>[];
  } | null;
  error?: string;
  steps: {
    id: number;
    key: string;
    title: string;
    tool: string;
    status: string;
    output?: Record<string, unknown> | null;
    error?: string | null;
  }[];
};
const iconFor = (tool: string) =>
  tool.includes("research") ? (
    <Globe2 size={16} />
  ) : tool.includes("csv") ? (
    <FileText size={16} />
  ) : (
    <LockKeyhole size={16} />
  );
export default function App() {
  const [page, setPage] = useState("Overview"),
    [task, setTask] = useState(
      "Research the public product pricing pages I provide, compare the displayed information, and create a CSV report.",
    ),
    [urls, setUrls] = useState("https://example.com"),
    [plan, setPlan] = useState<Plan | null>(null),
    [run, setRun] = useState<Run | null>(null),
    [workflows, setWorkflows] = useState<Workflow[]>([]),
    [runs, setRuns] = useState<Run[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [apiOnline, setApiOnline] = useState(false),
    [mobileOpen, setMobileOpen] = useState(false);
  const refresh = async () => {
    if (!API) {
      setApiOnline(false);
      return;
    }
    try {
      let [w, r] = await Promise.all([
        fetch(`${API}/workflows`),
        fetch(`${API}/runs`),
      ]);
      if (!w.ok || !r.ok) throw Error("API unavailable");
      setWorkflows(await w.json());
      setRuns(await r.json());
      setApiOnline(true);
    } catch {
      setApiOnline(false);
    }
  };
  useEffect(() => {
    void refresh();
  }, []);
  useEffect(() => {
    if (!API || !run || !["pending", "running"].includes(run.status)) return;
    const timer = setInterval(async () => {
      try {
        const res = await fetch(`${API}/runs/${run.id}`);
        if (res.ok) {
          const next = await res.json();
          setRun(next);
          if (!["pending", "running"].includes(next.status)) {
            void refresh();
          }
        }
      } catch {}
    }, 1200);
    return () => clearInterval(timer);
  }, [run?.id, run?.status]);
  const createPlan = async () => {
    if (!API) {
      setError(
        "This GitHub Pages preview has no API configured. Set VITE_API_BASE to a hosted backend URL to enable workflow planning.",
      );
      return;
    }
    setError("");
    setBusy(true);
    try {
      const res = await fetch(`${API}/plans`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task,
          source_urls: urls
            .split(/[\n,]+/)
            .map((x: string) => x.trim())
            .filter(Boolean),
        }),
      });
      const data = await res.json();
      if (!res.ok) throw Error(data.detail || "Could not create a plan");
      setPlan(data);
      setRun(null);
    } catch (e) {
      setError(
        e instanceof Error
          ? e.message
          : "API unavailable. Start the backend and try again.",
      );
    } finally {
      setBusy(false);
    }
  };
  const approveRun = async () => {
    if (!API || !plan) return;
    setError("");
    setBusy(true);
    try {
      let res = await fetch(`${API}/workflows`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(plan),
      });
      let wf = await res.json();
      if (!res.ok) throw Error(wf.detail || "Could not save workflow");
      res = await fetch(`${API}/workflows/${wf.id}/runs`, { method: "POST" });
      let newRun = await res.json();
      if (!res.ok) throw Error(newRun.detail || "Could not start execution");
      setRun(newRun);
      setPlan(null);
      setPage("Executions");
      void refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start execution");
    } finally {
      setBusy(false);
    }
  };
  const nav = [
    ["Overview", LayoutDashboard],
    ["AI Agent", Bot],
    ["Workflow Builder", WorkflowIcon],
    ["Workflow Library", ListChecks],
    ["Executions", Activity],
    ["Browser Sessions", Globe2],
    ["Approvals", BadgeCheck],
    ["Integrations", Settings2],
    ["Artifacts", FileText],
    ["Audit Logs", Shield],
    ["Settings", Settings2],
  ] as const;
  const availablePages = new Set([
    "Overview",
    "AI Agent",
    "Workflow Builder",
    "Workflow Library",
    "Executions",
  ]);
  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <Sparkles size={18} />
          </div>
          <div>
            <b>agentos</b>
            <span>AI AUTOMATION</span>
          </div>
          <button className="close-nav" onClick={() => setMobileOpen(false)}>
            <X size={17} />
          </button>
        </div>
        <div className="workspace">
          <span className="workspace-logo">A</span>
          <div>
            <b>{workspaceLabel}</b>
            <small>{environmentLabel}</small>
          </div>
          <ChevronDown size={14} />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav>
          {nav.map(([label, Icon]) => (
            <button
              key={label}
              disabled={!availablePages.has(label)}
              title={
                !availablePages.has(label)
                  ? "Not available in this release"
                  : undefined
              }
              onClick={() => {
                if (availablePages.has(label)) setPage(label);
                setMobileOpen(false);
              }}
              className={`nav-item ${page === label ? "active" : ""} ${!availablePages.has(label) ? "disabled" : ""}`}
            >
              <Icon size={17} />
              <span>{label}</span>
              {!availablePages.has(label) && <small>Soon</small>}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="plan-card">
            <div className="plan-icon">
              <Shield size={16} />
            </div>
            <b>Review before running</b>
            <p>
              Review each workflow before execution. Email remains a local
              draft.
            </p>
            <button onClick={() => setPage("AI Agent")}>
              Review a plan <ArrowRight size={13} />
            </button>
          </div>
          <div className="profile">
            <div className="avatar">LD</div>
            <div>
              <b>Demo user</b>
              <small>{environmentLabel}</small>
            </div>
            <Settings2 size={16} />
          </div>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setMobileOpen(!mobileOpen)}
          >
            <Menu size={18} />
          </button>
          <div className="breadcrumbs">
            <span>Workspace</span>
            <span className="slash">/</span>
            <b>{page}</b>
          </div>
          <div className="top-actions">
            <span className={`api-status ${apiOnline ? "online" : ""}`}>
              <i />
              {apiOnline ? "API connected" : "API offline"}
            </span>
            <button className="help-btn" title="Help">
              <CircleHelp size={18} />
            </button>
            <div className="avatar small">LD</div>
          </div>
        </header>
        <div className="page-content">
          {hostedStaticPreview && (
            <div className="info-banner" role="status">
              This GitHub Pages site hosts the interface. Workflow planning,
              execution, and saved results need a separately hosted API.
            </div>
          )}
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                <span className="pulse" />
                AUTONOMOUS WORKSPACE
              </div>
              <h1>{page === "Overview" ? "Workspace overview" : page}</h1>
              <p>
                {page === "Overview"
                  ? "Monitor local workflow plans and recent executions."
                  : page === "AI Agent"
                    ? "Describe an outcome. Review the plan. Approve when you are ready."
                    : page === "Executions"
                      ? "Follow every step, inspect its evidence, and download the results."
                      : "Your workflows, organized and ready to run."}
              </p>
            </div>
            <button
              className="btn primary"
              onClick={() => {
                setPage("AI Agent");
                setPlan(null);
              }}
            >
              <Plus size={16} />
              New workflow
            </button>
          </div>
          {error && (
            <div className="error-banner">
              <X size={16} />
              {error}
              <button onClick={() => setError("")}>
                <X size={14} />
              </button>
            </div>
          )}
          {page === "AI Agent" || plan ? (
            <section className="agent-layout">
              <div className="panel composer">
                <div className="panel-head">
                  <div className="head-icon violet">
                    <Sparkles size={16} />
                  </div>
                  <div>
                    <h2>What should your agent do?</h2>
                    <p>
                      Start with an outcome. Your agent will turn it into a
                      reviewable plan.
                    </p>
                  </div>
                  <span className="mode-pill">DETERMINISTIC MODE</span>
                </div>
                <label className="field-label">YOUR INSTRUCTIONS</label>
                <textarea
                  value={task}
                  onChange={(e) => setTask(e.target.value)}
                  placeholder="e.g. Compare three public product pages and create a CSV report."
                />
                <label className="field-label">
                  PUBLIC SOURCE URLS <span>Optional · one URL per line</span>
                </label>
                <textarea
                  className="url-input"
                  value={urls}
                  onChange={(e) => setUrls(e.target.value)}
                  placeholder="https://example.com/product"
                />
                <div className="composer-foot">
                  <span>
                    <LockKeyhole size={13} />
                    Only public HTTP(S) pages are allowed
                  </span>
                  <button
                    className="btn primary"
                    disabled={busy || !apiOnline}
                    onClick={() => void createPlan()}
                  >
                    {busy ? (
                      <span className="spinner" />
                    ) : (
                      <Sparkles size={15} />
                    )}
                    Generate plan
                    <ArrowRight size={14} />
                  </button>
                </div>
              </div>
              <aside className="panel side-note">
                <div className="side-note-icon">
                  <Shield size={18} />
                </div>
                <h3>You stay in control</h3>
                <p>
                  Your plan is reviewed before it runs. Email drafts stay local
                  and are never sent.
                </p>
                <div className="note-rule" />
                <div className="note-row">
                  <span className="note-check">
                    <Check size={12} />
                  </span>
                  <span>Sources checked for safe public access</span>
                </div>
                <div className="note-row">
                  <span className="note-check">
                    <Check size={12} />
                  </span>
                  <span>Evidence captured with each result</span>
                </div>
                <div className="note-row">
                  <span className="note-check">
                    <Check size={12} />
                  </span>
                  <span>Every execution step is recorded</span>
                </div>
                <div className="adapter-note">
                  <b>Reader mode</b>
                  <span>Bounded HTTP · no browser session</span>
                </div>
              </aside>
              {plan && (
                <div className="panel plan-panel">
                  <div className="panel-head">
                    <div className="head-icon green">
                      <ListChecks size={16} />
                    </div>
                    <div>
                      <h2>Review your workflow</h2>
                      <p>Confirm the steps and source URLs before execution.</p>
                    </div>
                    <span className="status-pill pending">
                      <i />
                      AWAITING APPROVAL
                    </span>
                  </div>
                  <div className="plan-summary">
                    <span className="summary-label">GOAL</span>
                    <p>{plan.goal}</p>
                  </div>
                  <PlanCanvas plan={plan} />
                  <div className="workflow-steps">
                    {plan.steps.map((s, i) => (
                      <div className="workflow-step" key={s.id}>
                        <div className="step-icon">{iconFor(s.tool)}</div>
                        <div className="step-copy">
                          <b>{s.title}</b>
                          <p>{s.description}</p>
                          {s.tool === "research_public_pages" && (
                            <div className="source-tags">
                              {plan.source_urls.length ? (
                                plan.source_urls.map((u) => (
                                  <span key={u}>
                                    <Globe2 size={11} />
                                    {u}
                                  </span>
                                ))
                              ) : (
                                <span className="warning-tag">
                                  No source URLs supplied
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <span className="step-number">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                      </div>
                    ))}
                  </div>
                  <div className="risk-callout">
                    <Shield size={15} />
                    <span>
                      {plan.risks[0]} {plan.risks[1]}
                    </span>
                  </div>
                  <div className="plan-actions">
                    <button
                      className="btn secondary"
                      onClick={() => setPlan(null)}
                    >
                      Reject plan
                    </button>
                    <button
                      className="btn primary"
                      disabled={busy || plan.source_urls.length === 0}
                      onClick={() => void approveRun()}
                    >
                      {busy ? (
                        <span className="spinner" />
                      ) : (
                        <Check size={15} />
                      )}
                      Approve &amp; run
                      <ArrowRight size={14} />
                    </button>
                  </div>
                  {plan.source_urls.length === 0 && (
                    <p className="inline-warning">
                      Add at least one public source URL before approving this
                      research workflow.
                    </p>
                  )}
                </div>
              )}
            </section>
          ) : page === "Executions" ? (
            <section className="panel execution-panel">
              <div className="panel-head">
                <div className="head-icon blue">
                  <Activity size={16} />
                </div>
                <div>
                  <h2>Execution history</h2>
                  <p>Recent runs and their outcomes.</p>
                </div>
                <span className="count-pill">{runs.length} runs</span>
              </div>
              {run && <RunInspector run={run} />}
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>EXECUTION</th>
                      <th>STATUS</th>
                      <th>STARTED</th>
                      <th>RESULT</th>
                    </tr>
                  </thead>
                  <tbody>
                    {runs.map((r) => (
                      <tr
                        key={r.id}
                        onClick={() => setRun(r)}
                        className="click-row"
                      >
                        <td>
                          <b>Run #{r.id}</b>
                          <small>Workflow #{r.workflow_id}</small>
                        </td>
                        <td>
                          <Status status={r.status} />
                        </td>
                        <td>{new Date(r.created_at).toLocaleString()}</td>
                        <td>
                          {r.result?.record_count !== undefined
                            ? `${r.result.record_count} records`
                            : r.error || "—"}
                        </td>
                      </tr>
                    ))}
                    {!runs.length && (
                      <tr>
                        <td colSpan={4} className="empty-cell">
                          No executions yet. Create a workflow to get started.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          ) : page === "Workflow Library" || page === "Workflow Builder" ? (
            <section className="panel execution-panel">
              <div className="panel-head">
                <div className="head-icon violet">
                  <WorkflowIcon size={16} />
                </div>
                <div>
                  <h2>Saved workflows</h2>
                  <p>Saved plans from your workspace.</p>
                </div>
                <span className="count-pill">{workflows.length} workflows</span>
              </div>
              <div className="workflow-cards">
                {workflows.map((w) => (
                  <article className="library-card" key={w.id}>
                    <div className="card-top">
                      <div className="head-icon violet">
                        {iconFor("research")}
                      </div>
                      <span className="version">v{w.version}</span>
                    </div>
                    <h3>{w.name}</h3>
                    <p>
                      {w.definition.steps.length} steps ·{" "}
                      {w.definition.source_urls.length} public sources
                    </p>
                    <button
                      className="text-btn"
                      onClick={() => {
                        setPlan(w.definition);
                        setTask(w.goal);
                        setUrls(w.definition.source_urls.join("\n"));
                        setPage("AI Agent");
                      }}
                    >
                      Open workflow
                      <ArrowRight size={14} />
                    </button>
                  </article>
                ))}
                {!workflows.length && (
                  <div className="empty-library">
                    <WorkflowIcon size={25} />
                    <b>Your workflow library is ready</b>
                    <span>Plans you approve will appear here.</span>
                  </div>
                )}
              </div>
            </section>
          ) : (
            <>
              <section className="stats-grid">
                <Stat
                  icon={<Activity />}
                  label="TOTAL EXECUTIONS"
                  value={runs.length}
                  detail="Across all workflows"
                  tone="blue"
                />
                <Stat
                  icon={<BadgeCheck />}
                  label="SUCCESSFUL"
                  value={runs.filter((r) => r.status === "completed").length}
                  detail="Completed runs"
                  tone="green"
                />
                <Stat
                  icon={<X />}
                  label="FAILED"
                  value={runs.filter((r) => r.status === "failed").length}
                  detail="Runs that need attention"
                  tone="red"
                />
                <Stat
                  icon={<Clock3 />}
                  label="ACTIVE RUNS"
                  value={
                    runs.filter((r) =>
                      ["pending", "running"].includes(r.status),
                    ).length
                  }
                  detail="Queued or running"
                  tone="amber"
                />
              </section>
              <section className="dashboard-grid">
                <div className="panel recent-panel">
                  <div className="panel-head">
                    <div className="head-icon blue">
                      <Activity size={16} />
                    </div>
                    <div>
                      <h2>Recent executions</h2>
                      <p>A live view of your latest agent activity.</p>
                    </div>
                    <button
                      className="text-btn"
                      onClick={() => setPage("Executions")}
                    >
                      View all
                      <ArrowRight size={14} />
                    </button>
                  </div>
                  {runs.length ? (
                    <div className="recent-list">
                      {runs.slice(0, 5).map((r) => (
                        <div className="recent-row" key={r.id}>
                          <div className="recent-icon">
                            <Activity size={15} />
                          </div>
                          <div className="recent-main">
                            <b>Research workflow · #{r.id}</b>
                            <span>
                              {new Date(r.created_at).toLocaleString()}
                            </span>
                          </div>
                          <Status status={r.status} />
                          <button
                            className="row-open"
                            onClick={() => {
                              setRun(r);
                              setPage("Executions");
                            }}
                          >
                            <ArrowRight size={15} />
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">
                      <div className="empty-visual">
                        <div className="empty-orbit one" />
                        <div className="empty-orbit two" />
                        <Sparkles size={20} />
                      </div>
                      <b>Nothing running right now</b>
                      <span>Your recent agent activity will show up here.</span>
                      <button
                        className="btn secondary"
                        onClick={() => setPage("AI Agent")}
                      >
                        <Plus size={14} />
                        Create your first workflow
                      </button>
                    </div>
                  )}
                </div>
                <div className="panel quick-panel">
                  <div className="panel-head">
                    <div className="head-icon violet">
                      <Sparkles size={16} />
                    </div>
                    <div>
                      <h2>Quick start</h2>
                      <p>Put an agent to work in three steps.</p>
                    </div>
                  </div>
                  <div className="quick-steps">
                    <div>
                      <span>01</span>
                      <div>
                        <b>Describe a task</b>
                        <p>Tell the agent what outcome you need.</p>
                      </div>
                    </div>
                    <ArrowDown size={14} />
                    <div>
                      <span>02</span>
                      <div>
                        <b>Review the plan</b>
                        <p>Check every step before it runs.</p>
                      </div>
                    </div>
                    <ArrowDown size={14} />
                    <div>
                      <span>03</span>
                      <div>
                        <b>Verify the result</b>
                        <p>Inspect evidence and download artifacts.</p>
                      </div>
                    </div>
                  </div>
                  <button
                    className="btn primary wide"
                    onClick={() => setPage("AI Agent")}
                  >
                    <Sparkles size={15} />
                    Try the AI agent
                    <ArrowRight size={14} />
                  </button>
                </div>
              </section>
              <section className="bottom-grid">
                <div className="panel library-preview">
                  <div className="panel-head">
                    <div className="head-icon violet">
                      <WorkflowIcon size={16} />
                    </div>
                    <div>
                      <h2>Workflow library</h2>
                      <p>Your reusable automations.</p>
                    </div>
                    <button
                      className="text-btn"
                      onClick={() => setPage("Workflow Library")}
                    >
                      Browse library
                      <ArrowRight size={14} />
                    </button>
                  </div>
                  <div className="mini-workflows">
                    {workflows.slice(0, 3).map((w) => (
                      <div className="mini-flow" key={w.id}>
                        <div className="mini-icon">
                          <WorkflowIcon size={15} />
                        </div>
                        <div>
                          <b>{w.name}</b>
                          <small>
                            {w.definition.steps.length} steps · v{w.version}
                          </small>
                        </div>
                        <ArrowRight size={14} />
                      </div>
                    ))}
                    {!workflows.length && (
                      <div className="mini-empty">
                        Approved workflows will be saved here for reuse.
                      </div>
                    )}
                  </div>
                </div>
                <div className="panel security-panel">
                  <div className="panel-head">
                    <div className="head-icon green">
                      <Shield size={16} />
                    </div>
                    <div>
                      <h2>Workspace health</h2>
                      <p>Runtime and safety configuration.</p>
                    </div>
                  </div>
                  <div className="health-row">
                    <span>
                      <i
                        className={
                          apiOnline ? "health-dot green-dot" : "health-dot"
                        }
                      />
                      {apiOnline ? "Backend connected" : "Backend offline"}
                    </span>
                    <small>
                      {apiOnline
                        ? "Healthy"
                        : hostedStaticPreview
                          ? "API URL not configured"
                          : "Start API on :8000"}
                    </small>
                  </div>
                  <div className="health-row">
                    <span>
                      <i className="health-dot green-dot" />
                      Execution reader
                    </span>
                    <small>Bounded HTTP</small>
                  </div>
                  <div className="health-row">
                    <span>
                      <i className="health-dot green-dot" />
                      Email integration
                    </span>
                    <small>Draft only</small>
                  </div>
                </div>
              </section>
            </>
          )}
          <footer>
            AgentOS AI <span>·</span> Development environment{" "}
            <span className="footer-right">
              Built for safe, observable automation
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
function PlanCanvas({ plan }: { plan: Plan }) {
  const nodes: Node[] = plan.steps.map((step, index) => ({
    id: step.id,
    position: { x: index * 245, y: 24 },
    data: { label: `${String(index + 1).padStart(2, "0")}  ${step.title}` },
    style: {
      width: 190,
      padding: 12,
      borderRadius: 8,
      background: "#20242b",
      border: "1px solid #3b424e",
      color: "#e4e7ec",
      fontSize: 10,
      fontWeight: 600,
    },
  }));
  const edges: Edge[] = plan.steps.flatMap((step) =>
    step.depends_on.map((dep) => ({
      id: `${dep}-${step.id}`,
      source: dep,
      target: step.id,
      animated: false,
      style: { stroke: "#69c8c3", strokeWidth: 1.5 },
    })),
  );
  return (
    <div className="plan-canvas">
      <div className="canvas-label">
        <WorkflowIcon size={13} />
        WORKFLOW CANVAS <span>Drag nodes to arrange</span>
      </div>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        nodesDraggable
        nodesConnectable={false}
        elementsSelectable
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#39404a" gap={18} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
function Stat({
  icon,
  label,
  value,
  detail,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  detail: string;
  tone: string;
}) {
  return (
    <div className="panel stat-card">
      <div className={`stat-icon ${tone}`}>{icon}</div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-detail">{detail}</div>
    </div>
  );
}
function Status({ status }: { status: string }) {
  return (
    <span className={`status-pill ${status}`}>
      <i />
      {status.replace("_", " ")}
    </span>
  );
}
function RunInspector({ run }: { run: Run }) {
  return (
    <div className="run-inspector">
      <div className="run-inspector-head">
        <div>
          <span className="eyebrow">EXECUTION #{run.id}</span>
          <h3>
            {run.status === "completed"
              ? "Research complete"
              : run.status === "failed"
                ? "Execution failed"
                : "Agent is working"}
          </h3>
        </div>
        <Status status={run.status} />
      </div>
      {run.error && <div className="error-inline">{run.error}</div>}
      <div className="timeline">
        {run.steps.map((s, i) => (
          <div className={`timeline-step ${s.status}`} key={s.id}>
            <div className="timeline-marker">
              {s.status === "completed" ? (
                <Check size={13} />
              ) : s.status === "running" ? (
                <span className="spinner" />
              ) : (
                <span>{i + 1}</span>
              )}
            </div>
            <div className="timeline-copy">
              <b>{s.title}</b>
              <span>
                {s.status}
                {s.error ? ` · ${s.error}` : ""}
              </span>
              {s.output && s.tool === "research_public_pages" && (
                <small>
                  {Array.isArray(s.output.records)
                    ? `${(s.output.records as unknown[]).length} source records · Bounded HTTP reader`
                    : ""}
                </small>
              )}
              {s.output && s.tool === "prepare_email_draft" && (
                <small>Email draft prepared locally · not sent</small>
              )}
            </div>
            {s.output &&
              s.tool === "generate_csv" &&
              typeof s.output.artifact_id === "number" && (
                <a
                  className="download-link"
                  href={
                    API
                      ? `${API}/artifacts/${s.output.artifact_id}/download`
                      : undefined
                  }
                >
                  <Download size={14} />
                  CSV
                </a>
              )}
          </div>
        ))}
      </div>
      {run.result && (
        <div className="result-strip">
          <BadgeCheck size={16} />
          <span>
            <b>{run.result.record_count} research records</b> ·{" "}
            {run.result.reader} reader · email not sent
          </span>
        </div>
      )}
      {run.result?.records?.length && (
        <div className="evidence-list">
          <b>Collected evidence</b>
          {run.result.records.map((r, i) => (
            <div className="evidence-row" key={i}>
              <Globe2 size={14} />
              <div>
                <b>{r.title || "Untitled page"}</b>
                <a href={r.source_url} target="_blank" rel="noreferrer">
                  {r.source_url}
                </a>
                <p>
                  {r.description ||
                    r.evidence ||
                    r.error ||
                    "No visible description extracted."}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Check, ChevronDown, ChevronRight, CornerDownRight, RefreshCw } from "lucide-react";
import { AGENTS } from "../../lib/api";
import { IconButton, Pill } from "./Controls";

function AgentOutput({ agent, output, live, busy, onContinue }) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  useEffect(() => { setDraft(output ? JSON.stringify(output, null, 2) : ""); setError(""); }, [output]);
  if (!output) return <div className="agent-output" data-testid={`agent-output-${agent.toLowerCase()}`}>{live || "Waiting for a run…"}</div>;
  const submit = () => { try { onContinue(agent, JSON.parse(draft)); setError(""); } catch { setError("Not valid JSON"); } };
  const dirty = draft !== JSON.stringify(output, null, 2);
  return <div className="agent-edit">
    <textarea data-testid={`agent-output-${agent.toLowerCase()}`} value={draft} onChange={(e) => setDraft(e.target.value)} spellCheck={false} />
    {error && <small className="agent-error" data-testid={`agent-json-error-${agent.toLowerCase()}`}>{error}</small>}
    <button className="continue-button" data-testid={`agent-continue-${agent.toLowerCase()}`} disabled={busy} onClick={submit}><CornerDownRight size={12} /> {dirty ? "Apply edit & continue" : "Continue from here"}</button>
  </div>;
}

export function AgentTimeline({ statuses, outputs, live, errors, busy, onRerun, onContinue }) {
  const [expanded, setExpanded] = useState("");
  return <div className="timeline" data-testid="agent-timeline">
    <div className="section-heading"><div><span className="eyebrow">PIPELINE</span><h3>Agent timeline</h3></div><Pill tone="live"><Activity size={12} /> SEQUENTIAL</Pill></div>
    {AGENTS.map((agent, index) => {
      const status = statuses[agent] || "waiting";
      const open = expanded === agent || status === "running";
      return <div className={`agent-row ${status}`} key={agent} data-testid={`agent-row-${agent.toLowerCase()}`}>
        <div className="agent-index">{status === "done" ? <Check size={14} /> : status === "running" || status === "retry" ? <span className="spinner" /> : status === "error" ? <AlertTriangle size={12} /> : String(index + 1).padStart(2, "0")}</div>
        <div className="agent-main">
          <button className="agent-name" data-testid={`agent-expand-${agent.toLowerCase()}`} onClick={() => setExpanded(expanded === agent ? "" : agent)}>{open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}{agent}</button>
          {errors[agent] && <small className="agent-error" data-testid={`agent-error-${agent.toLowerCase()}`}>{errors[agent]}</small>}
          {open && <AgentOutput agent={agent} output={outputs[agent]} live={live[agent]} busy={busy} onContinue={onContinue} />}
        </div>
        <div className="agent-meta">
          <span className={live[agent] === "rules" && status === "done" ? "rules-label" : `${status}-label`} data-testid={`agent-status-${agent.toLowerCase()}`}>{status === "waiting" ? "--:--" : status === "skipped" ? "SKIP" : live[agent] === "rules" && status === "done" ? "RULES" : status.toUpperCase()}</span>
          <IconButton label={`Rerun ${agent}`} disabled={busy} onClick={() => onRerun(agent)}><RefreshCw size={12} /></IconButton>
        </div>
      </div>;
    })}
  </div>;
}

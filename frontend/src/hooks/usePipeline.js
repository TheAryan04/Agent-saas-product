import { useState } from "react";
import { AGENTS, OPTIONAL_AGENTS, runPipeline } from "../lib/api";

export function usePipeline({ settings, onProject }) {
  const [statuses, setStatuses] = useState({});
  const [outputs, setOutputs] = useState({});
  const [live, setLive] = useState({});
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [failure, setFailure] = useState(null);

  const handle = (event) => {
    const agents = event.agents || (event.name ? event.name.split(" + ") : []);
    if (event.type === "agent") {
      setStatuses((s) => ({ ...s, ...Object.fromEntries(agents.map((a) => [a, event.status])) }));
      if (event.status === "running") setLive((l) => ({ ...l, ...Object.fromEntries(agents.map((a) => [a, ""])) }));
      if (event.status === "retry" || event.status === "error") setErrors((e) => ({ ...e, ...Object.fromEntries(agents.map((a) => [a, event.status === "retry" ? `Retrying — ${event.error.slice(0, 140)}` : event.error])) }));
      if (event.status === "done") {
        if (event.mode === "rules") setLive((l) => ({ ...l, ...Object.fromEntries(agents.map((a) => [a, "rules"])) }));
        setErrors((e) => { const next = { ...e }; agents.forEach((a) => delete next[a]); return next; });
        setOutputs((o) => ({ ...o, ...(agents.length > 1 ? event.output : { [agents[0]]: event.output }) }));
      }
    }
    if (event.type === "token") setLive((l) => ({ ...l, ...Object.fromEntries(agents.map((a) => [a, ((l[a] || "") + event.text).slice(-400)])) }));
    if (event.type === "error") setFailure(event);
    if (event.type === "complete") { setOutputs(event.outputs); onProject(event.project); }
  };

  const run = async (body, resetFrom) => {
    setBusy(true); setFailure(null);
    const reset = AGENTS.slice(resetFrom);
    const skip = (a) => (OPTIONAL_AGENTS.includes(a) && settings.enabled[a] === false) || (body.fast_mode && a === "Critic");
    setStatuses((s) => ({ ...s, ...Object.fromEntries(reset.map((a) => [a, skip(a) ? "skipped" : "waiting"])) }));
    setErrors((e) => Object.fromEntries(Object.entries(e).filter(([a]) => !reset.includes(a))));
    try { await runPipeline({ ...body, models: settings.models, enabled: settings.enabled }, handle); }
    catch (err) { setFailure({ code: "request_failed", message: err.message }); }
    finally { setBusy(false); setStatuses((s) => Object.fromEntries(Object.entries(s).map(([a, v]) => [a, v === "running" || v === "retry" ? "error" : v]))); }
  };

  const generate = (prompt, aspectRatio, fastMode) => { setOutputs({}); setLive({}); return run({ prompt, aspect_ratio: aspectRatio, fast_mode: fastMode }, 0); };
  const continueFrom = (agent, edited, prompt, aspectRatio) => {
    const merged = { ...outputs, ...(edited !== undefined ? { [agent]: edited } : {}) };
    setOutputs(merged);
    return run({ prompt, aspect_ratio: aspectRatio, from_agent: agent, outputs: merged }, AGENTS.indexOf(agent) + 1);
  };

  return { statuses, outputs, setOutputs, live, errors, busy, failure, setFailure, generate, continueFrom, setStatuses };
}

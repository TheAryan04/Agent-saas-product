import { useEffect, useState } from "react";
import axios from "axios";
import { ChevronRight } from "lucide-react";
import { AGENTS, API, MODELS, OPTIONAL_AGENTS } from "../../lib/api";

export function SettingsView({ settings, setSettings, ollama, onBack }) {
  const [caps, setCaps] = useState(null);
  useEffect(() => { axios.get(`${API}/render/capabilities`).then(({ data }) => setCaps(data)).catch(() => {}); }, []);
  const models = [...new Set([...(ollama.models || []), ...MODELS])];
  const setModel = (agent, model) => setSettings({ ...settings, models: { ...settings.models, [agent]: model } });
  const setEnabled = (agent, on) => setSettings({ ...settings, enabled: { ...settings.enabled, [agent]: on } });
  return <div className="settings-view">
    <button className="back-button" data-testid="settings-back-button" onClick={onBack}><ChevronRight size={16} /> Back to studio</button>
    <span className="eyebrow">LOCAL CONFIGURATION</span><h1>Pipeline settings</h1>
    <p>Every decision stays on this machine. Agents run one at a time. Planner, Orchestrator and Copywriter are required; the others can be skipped to save time.</p>
    <div className="settings-card">
      {AGENTS.map((agent) => <div className="setting-row" key={agent}>
        <div><b>{agent}</b><small>{OPTIONAL_AGENTS.includes(agent) ? "Optional · structured JSON + 1 retry" : "Required · structured JSON + 1 retry"}</small></div>
        <select data-testid={`model-select-${agent.toLowerCase()}`} value={settings.models[agent] || ollama.model || MODELS[0]} onChange={(e) => setModel(agent, e.target.value)}>{models.map((m) => <option key={m}>{m}</option>)}</select>
        <input type="checkbox" data-testid={`agent-toggle-${agent.toLowerCase()}`} checked={settings.enabled[agent] !== false || !OPTIONAL_AGENTS.includes(agent)} disabled={!OPTIONAL_AGENTS.includes(agent)} onChange={(e) => setEnabled(agent, e.target.checked)} />
      </div>)}
      <div className="health-box" data-testid="settings-ollama-health"><span className={ollama.running ? "health-dot good" : "health-dot"} /> <b>{ollama.running ? (ollama.model_pulled ? "Ollama is running" : "Ollama running, model not pulled") : "Ollama is offline"}</b><code>{ollama.fix}</code></div>
      <div className="health-box" data-testid="settings-voice-health"><span className={caps?.piper ? "health-dot good" : "health-dot"} /> <b>Piper voiceover {caps?.piper ? "ready" : "not installed"}</b><span className={caps?.whisper ? "health-dot good" : "health-dot"} style={{ marginLeft: 14 }} /> <b>whisper.cpp captions {caps?.whisper ? "ready" : "not installed"}</b></div>
    </div>
  </div>;
}

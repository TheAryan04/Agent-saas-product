import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Check, ChevronRight, Download, Loader2, Mic, Play, Subtitles } from "lucide-react";
import { API } from "../../lib/api";

const STEPS = [
  { id: "piper_engine", group: "Narration", title: "Install the Piper engine", hint: "Local text-to-speech. About 35 MB, installed into this app's Python environment." },
  { id: "voice", group: "Narration", title: "Download a voice", hint: "Pick the voice that reads each scene's voiceover line.", choices: "voices" },
  { id: "whisper_engine", group: "Captions", title: "Install the whisper.cpp engine", hint: "Local speech-to-text that times captions to the narration. About 5 MB." },
  { id: "whisper_model", group: "Captions", title: "Download a caption model", hint: "tiny.en is plenty for clean narration on a laptop CPU.", choices: "whisper_models" },
];

function SetupStep({ step, index, status, onStart }) {
  const options = step.choices ? status[step.choices] : null;
  const current = step.choices === "voices" ? status.config.voice : status.config.whisper_model;
  const [choice, setChoice] = useState(current);
  const ready = status.steps[step.id] && (!options || choice === current);
  const task = status.tasks[step.id];
  const running = task?.status === "running";
  const needsEngine = (step.id === "voice" && !status.steps.piper_engine) || (step.id === "whisper_model" && !status.steps.whisper_engine);
  return <div className={`setup-step ${ready ? "ready" : ""}`} data-testid={`setup-step-${step.id}`}>
    <div className="setup-index">{ready ? <Check size={14} /> : String(index + 1).padStart(2, "0")}</div>
    <div className="setup-main">
      <b>{step.title}</b><small>{step.hint}</small>
      {options && <select data-testid={`setup-choice-${step.id}`} value={choice} onChange={(e) => setChoice(e.target.value)}>{options.map((o) => <option key={o.id} value={o.id}>{o.label} · {o.size_mb} MB{o.downloaded ? " · downloaded" : ""}</option>)}</select>}
      {task && <div className="setup-task" data-testid={`setup-task-${step.id}`}><div className="render-bar"><i style={{ width: `${Math.round((task.progress || (running ? 0.08 : 0)) * 100)}%` }} /></div><span className={task.status === "error" ? "agent-error" : ""}>{task.log}</span></div>}
      <details className="setup-manual"><summary>Do it manually instead</summary><code>{status.manual[step.id]}</code></details>
    </div>
    <button className="setup-button" data-testid={`setup-run-${step.id}`} disabled={running || ready || needsEngine} onClick={() => onStart(step.id, choice)}>
      {running ? <Loader2 size={13} className="spin" /> : ready ? <Check size={13} /> : <Download size={13} />} {running ? "Working…" : ready ? "Ready" : needsEngine ? "Engine first" : options ? (options.find((o) => o.id === choice)?.downloaded ? "Use this" : "Download") : "Install"}
    </button>
  </div>;
}

export function VoiceSetupView({ onBack }) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [sampleUrl, setSampleUrl] = useState("");
  const [testing, setTesting] = useState(false);
  const timer = useRef(null);
  const load = () => axios.get(`${API}/voice/setup`).then(({ data }) => setStatus(data)).catch(() => setError("Local API unavailable."));
  useEffect(() => { load(); timer.current = setInterval(load, 1500); return () => clearInterval(timer.current); }, []);
  const start = async (step, choice) => { setError(""); try { await axios.post(`${API}/voice/setup/${step}`, { choice }); load(); } catch (e) { setError(e.response?.data?.detail || "Could not start this step."); } };
  const test = async () => {
    setTesting(true); setError("");
    try { const { data } = await axios.post(`${API}/voice/test`, { text: "This is your Frameforge narrator, running entirely on this machine." }, { responseType: "blob" }); setSampleUrl(URL.createObjectURL(data)); }
    catch { setError("Voice test failed."); } finally { setTesting(false); }
  };
  return <div className="settings-view" data-testid="voice-setup-view">
    <button className="back-button" data-testid="voice-setup-back-button" onClick={onBack}><ChevronRight size={16} /> Back</button>
    <span className="eyebrow">OPTIONAL · RUNS OFFLINE AFTER SETUP</span><h1>Voice setup</h1>
    <p>Four one-time steps add narration and captions to your exports. Downloads happen once; after that everything runs on this machine.</p>
    {error && <div className="agent-error" data-testid="voice-setup-error">{error}</div>}
    {!status ? <div className="empty-projects">Checking local tools…</div> : <>
      <div className="setup-summary">
        <span data-testid="voice-narration-status" className={status.piper ? "ok" : ""}><Mic size={14} /> Narration {status.piper ? "ready" : "not set up"}</span>
        <span data-testid="voice-captions-status" className={status.whisper ? "ok" : ""}><Subtitles size={14} /> Captions {status.whisper ? "ready" : "not set up"}</span>
      </div>
      {["Narration", "Captions"].map((group) => <div className="settings-card setup-card" key={group}><span className="eyebrow">{group.toUpperCase()}</span>
        {STEPS.map((step, i) => step.group === group && <SetupStep key={step.id} step={step} index={i} status={status} onStart={start} />)}
        {group === "Narration" && <div className="setup-test"><button className="setup-button" data-testid="voice-test-button" disabled={!status.piper || testing} onClick={test}>{testing ? <Loader2 size={13} className="spin" /> : <Play size={13} />} Test voice</button>{sampleUrl && <audio data-testid="voice-test-audio" src={sampleUrl} controls autoPlay />}</div>}
      </div>)}
    </>}
  </div>;
}

import { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { CircleHelp, Download, Film, FolderOpen, Gauge, Layers3, Save, Settings2, Sparkles, TerminalSquare, X } from "lucide-react";
import "@/App.css";
import { AGENTS, API, loadSettings, saveSettings } from "./lib/api";
import { SEED_PROJECT } from "./remotion/seed";
import { sceneFrames } from "./remotion/Film";
import { usePipeline } from "./hooks/usePipeline";
import { IconButton, Pill, Switch } from "./components/studio/Controls";
import { Preview } from "./components/studio/Preview";
import { AgentTimeline } from "./components/studio/AgentTimeline";
import { SceneEditor } from "./components/studio/SceneEditor";
import { ExportDialog } from "./components/studio/ExportDialog";
import { ProjectsView } from "./components/studio/ProjectsView";
import { SettingsView } from "./components/studio/SettingsView";
import { VoiceSetupView } from "./components/studio/VoiceSetupView";

function OfflineBanner({ failure, onRetry, onDismiss }) {
  const offline = failure.code === "ollama_offline";
  return <div className="offline-banner" data-testid={offline ? "ollama-offline-banner" : "pipeline-error-banner"}>
    <div className="offline-head"><TerminalSquare size={15} /><b>{offline ? "Ollama is offline" : "Pipeline stopped"}</b><button data-testid="dismiss-pipeline-error" aria-label="Dismiss" onClick={onDismiss}><X size={13} /></button></div>
    <p data-testid="pipeline-error-message">{failure.message}</p>
    {failure.fix && <code data-testid="ollama-fix-command">{failure.fix}</code>}
    <button className="retry-button" data-testid="pipeline-retry-button" onClick={onRetry}>Check again & retry</button>
  </div>;
}

function App() {
  const [project, setProject] = useState(SEED_PROJECT);
  const [selected, setSelected] = useState(0);
  const [prompt, setPrompt] = useState("Create a crisp launch film for a calm workspace where product teams turn ideas into momentum.");
  const [fastMode, setFastMode] = useState(false);
  const [view, setView] = useState("studio");
  const [ollama, setOllama] = useState({ running: false, models: [] });
  const [settings, setSettingsState] = useState(loadSettings);
  const [notice, setNotice] = useState("");
  const [exporting, setExporting] = useState(false);
  const player = useRef(null);
  const pipe = usePipeline({ settings, onProject: (next) => { setProject(next); setSelected(0); setNotice("Draft ready — edit, reorder or continue from any agent."); } });
  const totalDuration = useMemo(() => project.scenes.reduce((t, s) => t + Number(s.durationSec || 0), 0), [project]);

  const refreshHealth = () => axios.get(`${API}/health/ollama`).then(({ data }) => setOllama(data)).catch(() => {});
  useEffect(() => { refreshHealth(); }, []);
  useEffect(() => { const start = project.scenes.slice(0, selected).reduce((t, s) => t + sceneFrames(s), 0); player.current?.seekTo(start + 10); }, [selected]); // eslint-disable-line react-hooks/exhaustive-deps

  const setSettings = (next) => { setSettingsState(next); saveSettings(next); };
  const generate = () => { setNotice(""); refreshHealth(); pipe.generate(prompt, project.aspectRatio, fastMode); };
  const continueFrom = (agent, edited) => pipe.continueFrom(agent, edited, prompt, project.aspectRatio);
  const rerun = (agent) => { const i = AGENTS.indexOf(agent); if (i === 0) generate(); else if (pipe.outputs[AGENTS[i - 1]] || i > 2) continueFrom(AGENTS[i - 1]); else setNotice(`Run the pipeline once before rerunning ${agent}.`); };
  const save = async () => { try { await axios.post(`${API}/projects`, { name: project.title, scene_json: project, agent_outputs: { ...pipe.outputs, _prompt: prompt } }); setNotice("Project saved locally."); } catch { setNotice("Could not reach the local project database."); } };
  const open = (item) => { setProject(item.scene_json || SEED_PROJECT); const { _prompt, ...outs } = item.agent_outputs || {}; pipe.setOutputs(outs); pipe.setStatuses(Object.fromEntries(Object.keys(outs).map((a) => [a, "done"]))); if (_prompt) setPrompt(_prompt); setSelected(0); setView("studio"); };

  if (view === "voice") return <VoiceSetupView onBack={() => setView("studio")} />;
  if (view === "settings") return <SettingsView settings={settings} setSettings={setSettings} ollama={ollama} onBack={() => setView("studio")} onVoiceSetup={() => setView("voice")} />;
  if (view === "projects") return <ProjectsView onBack={() => setView("studio")} onOpen={open} />;
  return <div className="app-shell">
    <header className="topbar">
      <div className="brand-mark"><div className="brand-glyph">✦</div><div><b>FRAMEFORGE</b><span>LOCAL MOTION STUDIO</span></div></div>
      <nav><button className="nav-active" data-testid="nav-studio-button"><Film size={15} /> Studio</button><button data-testid="nav-projects-button" onClick={() => setView("projects")}><FolderOpen size={15} /> Projects</button></nav>
      <div className="top-actions"><span className="local-status" data-testid="ollama-status"><span className={ollama.running ? "health-dot good" : "health-dot"} /> {ollama.running ? (ollama.model_pulled ? "OLLAMA ONLINE" : "MODEL NOT PULLED") : "OLLAMA OFFLINE"}</span><IconButton label="Help"><CircleHelp size={17} /></IconButton><IconButton label="Settings" onClick={() => setView("settings")}><Settings2 size={17} /></IconButton></div>
    </header>
    <main className="workspace">
      <aside className="left-panel">
        <div className="panel-heading"><div><span className="eyebrow">NEW PROJECT</span><h3>Build a film</h3></div><Pill>LOCAL</Pill></div>
        <label className="prompt-label">Your brief<textarea data-testid="prompt-input" value={prompt} onChange={(e) => setPrompt(e.target.value)} /></label>
        <div className="control-row"><label>Aspect ratio<select data-testid="aspect-ratio-select" value={project.aspectRatio} onChange={(e) => setProject({ ...project, aspectRatio: e.target.value })}><option>16:9</option><option>9:16</option></select></label><label>Duration<div className="duration-display" data-testid="duration-display">{totalDuration.toFixed(1)}s <span>auto</span></div></label></div>
        <div className="fast-row"><div><b>Fast mode</b><small>1 AI call + instant rules, skips Critic</small></div><Switch on={fastMode} onChange={setFastMode} label="Toggle fast mode" testId="fast-mode-toggle" /></div>
        <button className="generate-button" data-testid="generate-button" disabled={pipe.busy} onClick={generate}><Sparkles size={17} /> {pipe.busy ? "Agents working…" : "Generate motion draft"} <span>⌘ ↵</span></button>
        {pipe.failure && <OfflineBanner failure={pipe.failure} onRetry={generate} onDismiss={() => pipe.setFailure(null)} />}
        <div className="local-note"><Gauge size={15} /><span><b>CPU-friendly pipeline</b><small>Agents run one at a time and keep Ollama warm.</small></span></div>
        <AgentTimeline statuses={pipe.statuses} outputs={pipe.outputs} live={pipe.live} errors={pipe.errors} busy={pipe.busy} onRerun={rerun} onContinue={continueFrom} />
      </aside>
      <section className="center-panel">
        <div className="project-bar"><div><span className="eyebrow">PROJECT</span><h2 data-testid="project-title">{project.title}</h2></div><div className="project-actions"><IconButton label="Save project" onClick={save}><Save size={16} /></IconButton><button className="export-button" data-testid="export-button" onClick={() => setExporting(true)}><Download size={15} /> Export MP4</button></div></div>
        <Preview ref={player} project={project} />
        <div className="below-preview"><div className="playback-strip"><button className="play-button" data-testid="play-preview-button" onClick={() => player.current?.toggle()}>▶</button><span className="play-label">Preview film</span><span className="muted">{project.aspectRatio} · {totalDuration.toFixed(1)} sec</span></div><div className="hint"><Layers3 size={14} /> Select a scene to jump the preview there</div></div>
        {notice && <div className="toast-notice" data-testid="notice-message">{notice}<button data-testid="dismiss-notice-button" onClick={() => setNotice("")}><X size={14} /></button></div>}
      </section>
      <SceneEditor project={project} setProject={setProject} selected={selected} setSelected={setSelected} />
    </main>
    {exporting && <ExportDialog project={project} onClose={() => setExporting(false)} onSetup={() => { setExporting(false); setView("voice"); }} />}
  </div>;
}

export default App;

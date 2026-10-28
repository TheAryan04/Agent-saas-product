import { useEffect, useRef, useState } from "react";
import axios from "axios";
import { Download, Film, Loader2, X } from "lucide-react";
import { API } from "../../lib/api";
import { Switch } from "./Controls";

function OptionRow({ title, hint, on, onChange, available, fix, testId }) {
  return <div className="export-option" data-testid={`${testId}-row`}>
    <div><b>{title}</b><small>{available ? hint : <span data-testid={`${testId}-unavailable`}>Not installed — {fix}</span>}</small></div>
    <Switch on={on} onChange={onChange} label={title} testId={`${testId}-toggle`} disabled={!available} />
  </div>;
}

export function ExportDialog({ project, onClose }) {
  const [caps, setCaps] = useState(null);
  const [voiceover, setVoiceover] = useState(false);
  const [captions, setCaptions] = useState(false);
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");
  const timer = useRef(null);
  useEffect(() => { axios.get(`${API}/render/capabilities`).then(({ data }) => setCaps(data)).catch(() => setError("Local API unavailable.")); return () => clearInterval(timer.current); }, []);
  const poll = (id) => { timer.current = setInterval(async () => { try { const { data } = await axios.get(`${API}/render/${id}`); setJob(data); if (data.status === "done" || data.status === "error") clearInterval(timer.current); } catch { clearInterval(timer.current); } }, 1200); };
  const start = async () => {
    setError("");
    try { const { data } = await axios.post(`${API}/render`, { project, voiceover, captions: voiceover && captions }); setJob(data); poll(data.id); }
    catch (e) { setError(typeof e.response?.data?.detail === "string" ? e.response.data.detail : "Could not start the render."); }
  };
  const running = job && (job.status === "queued" || job.status === "running");
  const pct = Math.round((job?.progress || 0) * 100);
  return <div className="modal-backdrop" data-testid="export-dialog">
    <div className="modal-card">
      <div className="panel-heading"><div><span className="eyebrow">LOCAL RENDER</span><h3>Export MP4</h3></div><button className="modal-close" data-testid="export-close-button" aria-label="Close" onClick={onClose}><X size={16} /></button></div>
      <p className="modal-copy">Remotion renders the exact preview composition on this machine, then encodes H.264 with FFmpeg. Expect roughly 5–10× real time on a laptop CPU.</p>
      {!caps ? <div className="modal-copy" data-testid="export-capabilities-loading">Checking local tools…</div> : <>
        <OptionRow title="Voiceover" hint="Piper reads each scene's voiceover line. Scenes stretch to fit the audio." on={voiceover} onChange={setVoiceover} available={caps.piper} fix={caps.piper_fix} testId="export-voiceover" />
        <OptionRow title="Captions" hint={voiceover ? "whisper.cpp transcribes the voiceover into burned-in captions." : "Turn on voiceover first."} on={captions && voiceover} onChange={setCaptions} available={caps.whisper && voiceover} fix={caps.whisper ? "turn on voiceover first" : caps.whisper_fix} testId="export-captions" />
        {!caps.remotion && <div className="agent-error" data-testid="export-remotion-missing">Remotion renderer not found. Run yarn install in frontend/.</div>}
      </>}
      {job && <div className="render-progress" data-testid="render-progress">
        <div className="render-stage"><span data-testid="render-stage">{job.stage}</span><b data-testid="render-percent">{pct}%</b></div>
        <div className="render-bar"><i style={{ width: `${pct}%` }} /></div>
        {job.status === "error" && <small className="agent-error" data-testid="render-error">{job.error}</small>}
      </div>}
      {error && <div className="agent-error" data-testid="export-error">{error}</div>}
      <div className="modal-actions">
        {job?.status === "done"
          ? <a className="export-button" data-testid="render-download-link" href={`${process.env.REACT_APP_BACKEND_URL}${job.download_url}`} download><Download size={15} /> Download MP4</a>
          : <button className="export-button" data-testid="render-start-button" disabled={!caps?.remotion || running} onClick={start}>{running ? <Loader2 size={15} className="spin" /> : <Film size={15} />} {running ? "Rendering…" : "Render MP4"}</button>}
      </div>
    </div>
  </div>;
}

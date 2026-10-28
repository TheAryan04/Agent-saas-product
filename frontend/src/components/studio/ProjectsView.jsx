import { useEffect, useState } from "react";
import axios from "axios";
import { ChevronRight, Copy, MonitorPlay, Plus } from "lucide-react";
import { API } from "../../lib/api";
import { IconButton } from "./Controls";

export function ProjectsView({ onBack, onOpen }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => { axios.get(`${API}/projects`).then(({ data }) => setProjects(data)).catch(() => setError("Could not reach the local project database.")).finally(() => setLoading(false)); }, []);
  const duplicate = async (project) => { try { const { data } = await axios.post(`${API}/projects/${project.id}/duplicate`); setProjects((items) => [data, ...items]); } catch { setError("Duplicate failed."); } };
  return <div className="projects-view">
    <button className="back-button" data-testid="projects-back-button" onClick={onBack}><ChevronRight size={16} /> Back to studio</button>
    <div className="projects-heading"><div><span className="eyebrow">LOCAL LIBRARY</span><h1>Projects <span>{String(projects.length).padStart(2, "0")}</span></h1></div><button className="generate-button new-project-button" data-testid="new-project-button" onClick={onBack}><Plus size={16} /> New project</button></div>
    <p className="projects-intro">Saved drafts stay on this machine, ready to reopen and keep shaping.</p>
    {error && <div className="agent-error" data-testid="projects-error">{error}</div>}
    <div className="projects-grid" data-testid="projects-list">{loading ? <div className="empty-projects">Loading local projects…</div> : projects.map((item) => <article className="project-card" key={item.id} data-testid={`project-card-${item.id}`}>
      <div className="project-thumb" style={{ background: item.scene_json?.brand?.background }}><span>{item.scene_json?.brand?.name || "LOCAL"}</span><b style={{ color: item.scene_json?.brand?.primaryColor }}>{item.scene_json?.title || item.name}</b><i>✦</i></div>
      <div className="project-card-meta"><div><b>{item.name}</b><small>{item.updated_at || "Saved locally"}</small></div><div className="project-card-actions"><IconButton label={`Open ${item.name}`} testId={`project-open-${item.id}`} onClick={() => onOpen(item)}><MonitorPlay size={14} /></IconButton><IconButton label={`Duplicate ${item.name}`} testId={`project-duplicate-${item.id}`} onClick={() => duplicate(item)}><Copy size={14} /></IconButton></div></div>
    </article>)}</div>
  </div>;
}

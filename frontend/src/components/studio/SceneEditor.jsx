import { useState } from "react";
import { Thumbnail } from "@remotion/player";
import { ArrowDown, ArrowUp, GripVertical, Plus, Trash2 } from "lucide-react";
import { TEMPLATES } from "../../lib/api";
import { Film, filmMeta, sceneFrames } from "../../remotion/Film";
import { IconButton } from "./Controls";

const EXTRA_FIELD = { CallToAction: ["button", "Button label"], SearchBar: ["query", "Search query"], SocialMockup: ["post", "Post text"], DeviceMockup: ["label", "Window address"], TextReveal: ["eyebrow", "Eyebrow"] };

export function move(list, from, to) {
  const next = [...list];
  const [item] = next.splice(from, 1);
  next.splice(to, 0, item);
  return next;
}

function SceneRow({ item, index, total, selected, project, startFrame, dragOver, onSelect, onMove, drag }) {
  const meta = filmMeta(project);
  const frame = Math.min(startFrame + sceneFrames(item) - 1, startFrame + 45);
  return <div className={`scene-item ${selected ? "selected" : ""} ${dragOver ? "drag-over" : ""}`} data-testid={`scene-item-${index}`} draggable onClick={onSelect} {...drag}>
    <GripVertical size={14} className="grip" data-testid={`scene-drag-handle-${index}`} />
    <span className={`scene-thumb ${meta.height > meta.width ? "vertical" : ""}`} data-testid={`scene-thumbnail-${index}`}>
      <Thumbnail component={Film} inputProps={{ project }} compositionWidth={meta.width} compositionHeight={meta.height} durationInFrames={meta.durationInFrames} fps={meta.fps} frameToDisplay={frame} style={{ width: "100%", display: "block" }} acknowledgeRemotionLicense />
    </span>
    <span className="scene-details"><b>{item.props?.headline || item.template}</b><small>{String(index + 1).padStart(2, "0")} · {item.template} · {Number(item.durationSec).toFixed(1)}s</small></span>
    <span className="scene-arrows" onClick={(e) => e.stopPropagation()}>
      <IconButton label={`Move scene ${index + 1} up`} testId={`scene-move-up-${index}`} disabled={index === 0} onClick={() => onMove(index, index - 1)}><ArrowUp size={11} /></IconButton>
      <IconButton label={`Move scene ${index + 1} down`} testId={`scene-move-down-${index}`} disabled={index === total - 1} onClick={() => onMove(index, index + 1)}><ArrowDown size={11} /></IconButton>
    </span>
  </div>;
}

function SceneForm({ scene, index, onChange, onDelete, canDelete }) {
  const setProp = (key, value) => onChange({ ...scene, props: { ...scene.props, [key]: value } });
  const extra = EXTRA_FIELD[scene.template];
  return <div className="editor-form">
    <div className="editor-form-head"><span>SCENE {String(index + 1).padStart(2, "0")}</span><IconButton label="Delete scene" disabled={!canDelete} onClick={onDelete}><Trash2 size={14} /></IconButton></div>
    <label>Template<select data-testid="scene-template-select" value={scene.template} onChange={(e) => onChange({ ...scene, template: e.target.value })}>{TEMPLATES.map((t) => <option key={t}>{t}</option>)}</select></label>
    <label>Headline<input data-testid="scene-headline-input" value={scene.props?.headline || ""} onChange={(e) => setProp("headline", e.target.value)} /></label>
    <label>Subline<input data-testid="scene-subline-input" value={scene.props?.subline || ""} onChange={(e) => setProp("subline", e.target.value)} /></label>
    {scene.template === "Flowchart" && <label>Steps <span className="input-suffix">comma separated</span><input data-testid="scene-steps-input" value={(scene.props?.steps || []).join(", ")} onChange={(e) => setProp("steps", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} /></label>}
    {extra && <label>{extra[1]}<input data-testid={`scene-${extra[0]}-input`} value={scene.props?.[extra[0]] || ""} onChange={(e) => setProp(extra[0], e.target.value)} /></label>}
    <label>Voiceover line<input data-testid="scene-voiceover-input" value={scene.props?.voiceover || ""} onChange={(e) => setProp("voiceover", e.target.value)} /></label>
    <label>Duration <span className="input-suffix">seconds</span><input data-testid="scene-duration-input" type="number" min="1" max="10" step="0.5" value={scene.durationSec} onChange={(e) => onChange({ ...scene, durationSec: Number(e.target.value) || 1 })} /></label>
  </div>;
}

export function SceneEditor({ project, setProject, selected, setSelected }) {
  const [dragFrom, setDragFrom] = useState(null);
  const [dragOver, setDragOver] = useState(null);
  const scenes = project.scenes;
  const scene = scenes[selected] || scenes[0];
  const reorder = (from, to) => {
    if (from === to || to < 0 || to >= scenes.length) return;
    setProject({ ...project, scenes: move(scenes, from, to) });
    setSelected(selected === from ? to : selected > from && selected <= to ? selected - 1 : selected < from && selected >= to ? selected + 1 : selected);
  };
  const update = (next) => setProject({ ...project, scenes: scenes.map((item, i) => (i === selected ? next : item)) });
  const remove = () => { if (scenes.length < 2) return; setProject({ ...project, scenes: scenes.filter((_, i) => i !== selected) }); setSelected(Math.max(0, selected - 1)); };
  const add = () => { setProject({ ...project, scenes: [...scenes, { template: "TextReveal", durationSec: 2, props: { headline: "New scene", transition: "fade", motion: "rise" } }] }); setSelected(scenes.length); };
  const dragProps = (index) => ({
    onDragStart: (e) => { setDragFrom(index); e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", String(index)); },
    onDragOver: (e) => { e.preventDefault(); setDragOver(index); },
    onDragLeave: () => setDragOver(null),
    onDrop: (e) => { e.preventDefault(); const from = dragFrom ?? Number(e.dataTransfer.getData("text/plain")); reorder(from, index); setDragFrom(null); setDragOver(null); },
    onDragEnd: () => { setDragFrom(null); setDragOver(null); },
  });
  return <aside className="right-panel" data-testid="scene-editor-panel">
    <div className="panel-heading"><div><span className="eyebrow">COMPOSITION</span><h3>Scenes <span className="count" data-testid="scene-count">{String(scenes.length).padStart(2, "0")}</span></h3></div></div>
    <p className="drag-hint">Drag to reorder, or use the arrows.</p>
    <div className="scene-list" data-testid="scene-list">{scenes.map((item, index) => <SceneRow key={`${index}-${item.template}`} item={item} index={index} total={scenes.length} selected={selected === index} project={project} startFrame={scenes.slice(0, index).reduce((t, s) => t + sceneFrames(s), 0)} dragOver={dragOver === index && dragFrom !== index} onSelect={() => setSelected(index)} onMove={reorder} drag={dragProps(index)} />)}</div>
    <div>
      {scene && <SceneForm scene={scene} index={selected} onChange={update} onDelete={remove} canDelete={scenes.length > 1} />}
      <button className="add-scene" data-testid="add-scene-button" onClick={add}><Plus size={15} /> Add scene</button>
    </div>
  </aside>;
}

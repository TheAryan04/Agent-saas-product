import React from "react";
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { TEMPLATES } from "./templates";
import { Backdrop, MONO, font, useUnit } from "./parts";

export const FPS = 30;
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" };

export const sceneFrames = (scene) => Math.max(15, Math.round(Number(scene.durationSec || 2) * FPS));

export function filmMeta(project) {
  const vertical = project.aspectRatio === "9:16";
  return { fps: FPS, width: vertical ? 720 : 1280, height: vertical ? 1280 : 720, durationInFrames: Math.max(1, project.scenes.reduce((t, s) => t + sceneFrames(s), 0)) };
}

function Transition({ type, duration, children }) {
  const frame = useCurrentFrame();
  const enter = interpolate(frame, [0, 12], [0, 1], clamp);
  const exit = interpolate(frame, [duration - 8, duration], [1, 0], clamp);
  const style = { opacity: Math.min(enter, exit) };
  if (type === "slide") style.transform = `translateX(${(1 - enter) * 8}%)`;
  if (type === "zoom") style.transform = `scale(${1.08 - enter * 0.08})`;
  if (type === "wipe") { style.opacity = exit; style.clipPath = `inset(0 ${(1 - enter) * 100}% 0 0)`; }
  return <AbsoluteFill style={style}>{children}</AbsoluteFill>;
}

function Chrome({ project, index }) {
  const { u, vertical } = useUnit();
  const pad = vertical ? 60 * u : 110 * u;
  const b = project.brand;
  return <>
    <div style={{ position: "absolute", left: pad, top: 44 * u, fontFamily: font(b), fontWeight: 700, fontSize: 20 * u, color: "#EEF3F2" }}>{b.name}<span style={{ color: b.primaryColor, marginLeft: 8 * u }}>●</span></div>
    <div style={{ position: "absolute", right: pad, top: 48 * u, fontFamily: MONO, fontSize: 14 * u, color: "#8995A0" }}>{String(index + 1).padStart(2, "0")} <span style={{ color: "#4F5B64" }}>/ {String(project.scenes.length).padStart(2, "0")}</span></div>
  </>;
}

function Captions({ captions, brand }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { u } = useUnit();
  const t = frame / fps;
  const active = (captions || []).find((c) => t >= c.start && t <= c.end);
  if (!active) return null;
  return <div style={{ position: "absolute", bottom: 54 * u, left: 0, right: 0, display: "flex", justifyContent: "center" }}><span style={{ background: "#000000B3", color: "#FFFFFF", fontFamily: font(brand), fontSize: 26 * u, padding: `${8 * u}px ${18 * u}px`, maxWidth: "80%", textAlign: "center", borderLeft: `3px solid ${brand.primaryColor}` }}>{active.text}</span></div>;
}

export function Film({ project }) {
  let from = 0;
  return <AbsoluteFill style={{ fontFamily: font(project.brand), overflow: "hidden" }}>
    <Backdrop brand={project.brand} />
    {project.scenes.map((scene, index) => {
      const duration = sceneFrames(scene);
      const Template = TEMPLATES[scene.template] || TEMPLATES.TextReveal;
      const seq = <Sequence key={index} from={from} durationInFrames={duration} name={`${index + 1} ${scene.template}`}>
        <Transition type={scene.props?.transition} duration={duration}><Template props={scene.props || {}} brand={project.brand} /></Transition>
        <Chrome project={project} index={index} />
        {scene.props?.audio && <Audio src={staticFile(scene.props.audio)} />}
      </Sequence>;
      from += duration;
      return seq;
    })}
    <Captions captions={project.captions} brand={project.brand} />
  </AbsoluteFill>;
}

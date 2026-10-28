import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Eyebrow, Headline, MONO, Stage, Sub, font, useEnter, useUnit } from "./parts";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" };

function TextReveal({ props, brand }) {
  return <Stage><Eyebrow brand={brand}>{props.eyebrow || brand.name}</Eyebrow><Headline text={props.headline} brand={brand} motion={props.motion} delay={4} size={92} /><Sub brand={brand} delay={18}>{props.subline}</Sub></Stage>;
}

function Flowchart({ props, brand }) {
  const frame = useCurrentFrame();
  const { u, vertical } = useUnit();
  const steps = (props.steps && props.steps.length ? props.steps : ["Plan", "Build", "Launch"]).slice(0, 4);
  return <Stage>
    <Eyebrow brand={brand}>{props.eyebrow}</Eyebrow>
    <Headline text={props.headline} brand={brand} motion={props.motion} size={60} />
    <div style={{ display: "flex", flexDirection: vertical ? "column" : "row", alignItems: vertical ? "stretch" : "center", gap: 14 * u, marginTop: 50 * u, width: vertical ? "100%" : undefined }}>
      {steps.map((step, i) => <React.Fragment key={i}>
        <Step index={i} step={step} brand={brand} delay={14 + i * 12} />
        {i < steps.length - 1 && <div style={{ background: brand.primaryColor, height: vertical ? 24 * u : 3, width: vertical ? 3 : 56 * u, alignSelf: "center", transformOrigin: vertical ? "top" : "left", transform: vertical ? `scaleY(${interpolate(frame, [22 + i * 12, 32 + i * 12], [0, 1], clamp)})` : `scaleX(${interpolate(frame, [22 + i * 12, 32 + i * 12], [0, 1], clamp)})` }} />}
      </React.Fragment>)}
    </div>
    <Sub brand={brand} delay={40}>{props.subline}</Sub>
  </Stage>;
}

function Step({ index, step, brand, delay }) {
  const { u } = useUnit();
  const style = useEnter(delay, "pop");
  return <div style={{ border: `1.5px solid ${brand.primaryColor}66`, background: `${brand.primaryColor}12`, padding: `${18 * u}px ${24 * u}px`, display: "flex", gap: 14 * u, alignItems: "center", ...style }}>
    <b style={{ fontFamily: MONO, color: brand.primaryColor, fontSize: 16 * u }}>{String(index + 1).padStart(2, "0")}</b>
    <span style={{ fontFamily: font(brand), color: "#EEF3F2", fontSize: 26 * u, fontWeight: 600 }}>{step}</span>
  </div>;
}

function SocialMockup({ props, brand }) {
  const frame = useCurrentFrame();
  const { u } = useUnit();
  const card = useEnter(10, "rise");
  const likes = Math.floor(interpolate(frame, [20, 70], [0, 1248], clamp));
  return <Stage>
    <Headline text={props.headline} brand={brand} motion={props.motion} size={54} />
    <div style={{ marginTop: 40 * u, width: Math.min(620 * u, 9999), maxWidth: "100%", background: "#121A22", border: "1px solid #2A3540", padding: 28 * u, boxShadow: `0 ${20 * u}px ${60 * u}px #00000066`, ...card }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14 * u }}>
        <div style={{ width: 48 * u, height: 48 * u, borderRadius: "50%", background: brand.primaryColor, color: "#06110D", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 22 * u, fontFamily: font(brand) }}>{brand.name.slice(0, 1)}</div>
        <div><div style={{ color: "#F1F5F4", fontFamily: font(brand), fontWeight: 700, fontSize: 20 * u }}>{brand.name}</div><div style={{ color: "#7D8A92", fontFamily: MONO, fontSize: 13 * u }}>@{brand.name.toLowerCase().replace(/\s/g, "")}</div></div>
      </div>
      <p style={{ color: "#D6DEDF", fontFamily: font(brand), fontSize: 23 * u, lineHeight: 1.4, margin: `${20 * u}px 0` }}>{props.post || props.subline || "Shipping something new today."}</p>
      <div style={{ display: "flex", gap: 30 * u, fontFamily: MONO, fontSize: 14 * u, color: "#7D8A92" }}><span style={{ color: brand.primaryColor }}>♥ {likes.toLocaleString("en-US")}</span><span>↻ {Math.floor(likes / 6)}</span><span>◎ {Math.floor(likes / 14)}</span></div>
    </div>
  </Stage>;
}

function SearchBar({ props, brand }) {
  const frame = useCurrentFrame();
  const { u } = useUnit();
  const query = props.query || props.headline || "";
  const chars = Math.floor(interpolate(frame, [8, 8 + query.length * 1.8], [0, query.length], clamp));
  const typedAt = 8 + query.length * 1.8;
  const rows = [props.headline, props.subline || `${brand.name} — answers in seconds`, props.label || "Docs · Guides · Changelog"].filter(Boolean);
  return <Stage>
    <Eyebrow brand={brand}>{props.eyebrow}</Eyebrow>
    <div style={{ width: "100%", maxWidth: 860 * u, border: `2px solid ${brand.primaryColor}`, background: "#0E151C", padding: `${22 * u}px ${28 * u}px`, display: "flex", alignItems: "center", gap: 18 * u, boxShadow: `0 0 ${40 * u}px ${brand.primaryColor}33` }}>
      <span style={{ color: brand.primaryColor, fontSize: 28 * u }}>⌕</span>
      <span style={{ color: "#F2F6F5", fontFamily: font(brand), fontSize: 32 * u }}>{query.slice(0, chars)}<span style={{ opacity: frame % 18 < 9 ? 1 : 0, color: brand.primaryColor }}>|</span></span>
    </div>
    <div style={{ width: "100%", maxWidth: 860 * u, marginTop: 14 * u }}>
      {rows.map((row, i) => <ResultRow key={i} text={row} first={i === 0} brand={brand} delay={typedAt + 4 + i * 6} />)}
    </div>
  </Stage>;
}

function ResultRow({ text, first, brand, delay }) {
  const { u } = useUnit();
  const style = useEnter(delay, "rise");
  return <div style={{ padding: `${16 * u}px ${22 * u}px`, borderBottom: "1px solid #24303A", background: first ? `${brand.primaryColor}14` : "transparent", color: first ? "#F4F7F6" : "#A8B3B7", fontFamily: font(brand), fontSize: (first ? 26 : 20) * u, fontWeight: first ? 700 : 400, ...style }}>{text}</div>;
}

function DeviceMockup({ props, brand }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { u, vertical } = useUnit();
  const rise = spring({ frame: frame - 6, fps, config: { damping: 18 } });
  const bars = [0.55, 0.8, 0.4, 0.95, 0.7, 0.6];
  return <Stage>
    <Headline text={props.headline} brand={brand} motion={props.motion} size={54} />
    <div style={{ marginTop: 36 * u, width: vertical ? "100%" : 820 * u, border: "1px solid #33414C", background: "#0F161D", transform: `translateY(${interpolate(rise, [0, 1], [120 * u, 0])}px)`, opacity: rise, boxShadow: `0 ${24 * u}px ${70 * u}px #00000080` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 * u, padding: `${12 * u}px ${16 * u}px`, borderBottom: "1px solid #26323C" }}>
        {["#FF6B6B", "#FFC86B", brand.primaryColor].map((c) => <i key={c} style={{ width: 11 * u, height: 11 * u, borderRadius: "50%", background: c, display: "block" }} />)}
        <span style={{ marginLeft: 14 * u, fontFamily: MONO, fontSize: 13 * u, color: "#8995A0", background: "#18212A", padding: `${5 * u}px ${14 * u}px`, flex: 1 }}>{props.label || `${brand.name.toLowerCase()}.app`}</span>
      </div>
      <div style={{ display: "flex", gap: 18 * u, padding: 22 * u, height: 250 * u }}>
        <div style={{ width: 130 * u, display: vertical ? "none" : "flex", flexDirection: "column", gap: 12 * u }}>{[0.9, 0.7, 0.8, 0.6].map((w, i) => <i key={i} style={{ display: "block", height: 10 * u, width: `${w * 100}%`, background: i === 0 ? brand.primaryColor : "#2A3843" }} />)}</div>
        <div style={{ flex: 1, display: "flex", alignItems: "flex-end", gap: 14 * u, borderLeft: "1px solid #24303A", paddingLeft: 18 * u }}>
          {bars.map((h, i) => <div key={i} style={{ flex: 1, height: `${interpolate(frame, [18 + i * 4, 40 + i * 4], [4, h * 100], clamp)}%`, background: i === 3 ? brand.primaryColor : `${brand.accentColor}66` }} />)}
        </div>
      </div>
    </div>
  </Stage>;
}

function CallToAction({ props, brand }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { u } = useUnit();
  const pop = spring({ frame: frame - 16, fps, config: { damping: 10, stiffness: 140 } });
  const pulse = (frame % 40) / 40;
  return <Stage center>
    <Headline text={props.headline} brand={brand} motion={props.motion} size={80} align="center" />
    <Sub brand={brand} delay={10} align="center">{props.subline}</Sub>
    <div style={{ position: "relative", marginTop: 48 * u, transform: `scale(${pop})` }}>
      <div style={{ position: "absolute", inset: 0, border: `2px solid ${brand.primaryColor}`, transform: `scale(${1 + pulse * 0.25})`, opacity: 1 - pulse }} />
      <div style={{ position: "relative", background: brand.primaryColor, color: "#06110D", fontFamily: font(brand), fontWeight: 700, fontSize: 28 * u, padding: `${20 * u}px ${38 * u}px` }}>{props.button || "Get started"} →</div>
    </div>
    <div style={{ marginTop: 40 * u, fontFamily: MONO, fontSize: 16 * u, letterSpacing: "0.2em", color: "#8E9AA3", opacity: interpolate(frame, [26, 40], [0, 1], clamp) }}>{brand.name.toUpperCase()}</div>
  </Stage>;
}

export const TEMPLATES = { TextReveal, Flowchart, SocialMockup, SearchBar, DeviceMockup, CallToAction };

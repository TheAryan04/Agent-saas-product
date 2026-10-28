import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export const MONO = "'DM Mono', 'JetBrains Mono', ui-monospace, monospace";
export const font = (brand) => `'${brand.font || "Outfit"}', 'Outfit', system-ui, sans-serif`;

export function useUnit() {
  const { width, height } = useVideoConfig();
  return { u: Math.min(width, height) / 720, vertical: height > width };
}

export function useEnter(delay = 0, motion = "rise") {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame - delay;
  const s = spring({ frame: t, fps, config: { damping: 16, stiffness: 120 } });
  const opacity = interpolate(t, [0, 10], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (motion === "pop") return { opacity, transform: `scale(${interpolate(s, [0, 1], [0.7, 1])})` };
  if (motion === "drift") return { opacity, transform: `translateX(${interpolate(t, [0, 40], [-36, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)` };
  return { opacity, transform: `translateY(${interpolate(s, [0, 1], [40, 0])}px)` };
}

export function Headline({ text = "", brand, motion = "rise", delay = 0, size = 72, align = "left" }) {
  const frame = useCurrentFrame();
  const { u } = useUnit();
  const words = text.split(" ");
  const base = { fontFamily: font(brand), fontSize: size * u, fontWeight: 700, lineHeight: 1.02, letterSpacing: "-0.03em", color: "#F4F7F6", margin: 0, textAlign: align };
  if (motion === "type") {
    const chars = Math.floor(interpolate(frame - delay, [0, text.length * 1.6], [0, text.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
    return <h1 style={base}>{text.slice(0, chars)}<span style={{ color: brand.primaryColor, opacity: frame % 20 < 10 ? 1 : 0 }}>|</span></h1>;
  }
  return <h1 style={base}>{words.map((word, i) => <Word key={i} word={word} last={i === words.length - 1} brand={brand} motion={motion} delay={delay + i * 4} />)}</h1>;
}

function Word({ word, last, brand, motion, delay }) {
  const style = useEnter(delay, motion);
  return <span style={{ display: "inline-block", marginRight: "0.25em", color: last ? brand.primaryColor : undefined, ...style }}>{word}</span>;
}

export function Eyebrow({ children, brand, delay = 0 }) {
  const { u } = useUnit();
  const style = useEnter(delay, "drift");
  if (!children) return null;
  return <div style={{ fontFamily: MONO, fontSize: 15 * u, letterSpacing: "0.18em", color: brand.accentColor, textTransform: "uppercase", marginBottom: 22 * u, ...style }}>{children} <span style={{ color: brand.primaryColor }}>✦</span></div>;
}

export function Sub({ children, brand, delay = 10, align = "left" }) {
  const { u } = useUnit();
  const style = useEnter(delay, "rise");
  if (!children) return null;
  return <p style={{ fontFamily: font(brand), fontSize: 24 * u, color: "#B9C4C6", maxWidth: 620 * u, margin: `${22 * u}px 0 0`, lineHeight: 1.35, textAlign: align, ...style }}>{children}</p>;
}

export function Backdrop({ brand }) {
  const frame = useCurrentFrame();
  const { u } = useUnit();
  const glowX = 70 + Math.sin(frame / 50) * 8;
  return <AbsoluteFill style={{ background: brand.background || "#0B1016" }}>
    <AbsoluteFill style={{ background: `radial-gradient(circle at ${glowX}% 20%, ${brand.primaryColor}33 0, transparent 45%), radial-gradient(circle at 10% 90%, ${brand.accentColor}22 0, transparent 40%)` }} />
    <AbsoluteFill style={{ opacity: 0.22, backgroundImage: `linear-gradient(${brand.primaryColor}22 1px, transparent 1px), linear-gradient(90deg, ${brand.primaryColor}22 1px, transparent 1px)`, backgroundSize: `${48 * u}px ${48 * u}px`, backgroundPosition: `0 ${frame * 0.4}px`, maskImage: "linear-gradient(to bottom, black, transparent 85%)", WebkitMaskImage: "linear-gradient(to bottom, black, transparent 85%)" }} />
  </AbsoluteFill>;
}

export function Stage({ children, center = false }) {
  const { u, vertical } = useUnit();
  return <AbsoluteFill style={{ padding: vertical ? `${170 * u}px ${60 * u}px` : `${90 * u}px ${110 * u}px`, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: center ? "center" : "flex-start", textAlign: center ? "center" : "left" }}>{children}</AbsoluteFill>;
}

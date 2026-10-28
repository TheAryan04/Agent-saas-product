import { forwardRef } from "react";
import { Player } from "@remotion/player";
import { Film, filmMeta } from "../../remotion/Film";
import { Pill } from "./Controls";

export const Preview = forwardRef(function Preview({ project }, ref) {
  const meta = filmMeta(project);
  const vertical = project.aspectRatio === "9:16";
  return <section className="preview-wrap" data-testid="video-preview-panel">
    <div className="preview-topline"><div className="eyebrow"><span className="live-dot" /> LIVE PREVIEW <span className="muted">/ {meta.width} × {meta.height} · {meta.fps} FPS · same composition as export</span></div><Pill tone="ready">REMOTION</Pill></div>
    <div className={`player-frame ${vertical ? "vertical" : ""}`} data-testid="video-preview-canvas">
      <Player ref={ref} component={Film} inputProps={{ project }} durationInFrames={meta.durationInFrames} compositionWidth={meta.width} compositionHeight={meta.height} fps={meta.fps}
        controls loop clickToPlay style={{ width: "100%", aspectRatio: `${meta.width} / ${meta.height}` }} acknowledgeRemotionLicense />
    </div>
  </section>;
});

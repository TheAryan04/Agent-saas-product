import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";

const [propsPath, outPath, publicDir] = process.argv.slice(2);
const here = path.dirname(fileURLToPath(import.meta.url));
const entryPoint = path.join(here, "..", "src", "remotion", "index.jsx");
const inputProps = JSON.parse(fs.readFileSync(propsPath, "utf8"));
const browserExecutable = process.env.REMOTION_BROWSER || null;
const concurrency = Number(process.env.REMOTION_CONCURRENCY || 1);

console.log("STAGE Bundling composition");
const serveUrl = await bundle({ entryPoint, publicDir, webpackOverride: (config) => config });
const composition = await selectComposition({ serveUrl, id: "Film", inputProps, browserExecutable });
console.log("STAGE Rendering frames");
let last = -1;
await renderMedia({
  composition, serveUrl, codec: "h264", outputLocation: outPath, inputProps, browserExecutable, concurrency,
  chromiumOptions: { gl: "swiftshader" }, x264Preset: "veryfast",
  onProgress: ({ progress }) => { const p = Math.floor(progress * 100); if (p !== last) { last = p; console.log(`PROGRESS ${progress.toFixed(3)}`); } },
});
console.log("STAGE Done");

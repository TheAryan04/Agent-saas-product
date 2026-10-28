import { useEffect, useState } from "react";
import { continueRender, delayRender } from "remotion";
import "@fontsource/outfit/400.css";
import "@fontsource/outfit/700.css";
import "@fontsource/manrope/400.css";
import "@fontsource/manrope/700.css";
import "@fontsource/sora/400.css";
import "@fontsource/sora/700.css";
import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/700.css";
import "@fontsource/space-mono/400.css";
import "@fontsource/space-mono/700.css";
import "@fontsource/dm-mono/400.css";

export const BRAND_FONTS = ["Outfit", "Manrope", "Sora", "IBM Plex Sans", "Space Mono"];

export function useBrandFont(family) {
  const name = BRAND_FONTS.includes(family) ? family : "Outfit";
  const [handle] = useState(() => delayRender(`Loading font ${name}`));
  useEffect(() => {
    Promise.all([`700 48px '${name}'`, `400 24px '${name}'`, "400 16px 'DM Mono'"].map((spec) => document.fonts.load(spec)))
      .finally(() => continueRender(handle));
  }, [handle, name]);
  return name;
}

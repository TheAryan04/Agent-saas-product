export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const AGENTS = ["Orchestrator", "Planner", "Copywriter", "Designer", "Director", "Critic"];
export const OPTIONAL_AGENTS = ["Designer", "Director", "Critic"];
export const TEMPLATES = ["TextReveal", "Flowchart", "SocialMockup", "SearchBar", "DeviceMockup", "CallToAction"];
export const MODELS = ["qwen2.5-coder:3b", "qwen2.5:3b", "llama3.2:3b"];

async function errorMessage(response) {
  const data = await response.json().catch(() => ({}));
  const detail = data.detail;
  const message = typeof detail === "string" ? detail : [detail?.message, ...(detail?.errors || [])].filter(Boolean).join(" — ");
  return message || `Request failed (${response.status})`;
}

async function readEvents(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop();
    chunks.forEach((chunk) => {
      const line = chunk.split("\n").find((item) => item.startsWith("data: "));
      if (line) onEvent(JSON.parse(line.slice(6)));
    });
  }
}

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Runs execute server-side; we reconnect from the last event so proxy time limits never cut a run short.
export async function runPipeline(body, onEvent) {
  const start = await fetch(`${API}/pipeline/runs`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!start.ok) throw new Error(await errorMessage(start));
  const { run_id: runId } = await start.json();
  let count = 0;
  let finished = false;
  let failures = 0;
  while (!finished) {
    try {
      const response = await fetch(`${API}/pipeline/runs/${runId}/events?after=${count}`);
      if (!response.ok) throw new Error(await errorMessage(response));
      await readEvents(response, (event) => { count += 1; if (event.type === "complete" || event.type === "error") finished = true; onEvent(event); });
      failures = 0;
    } catch (err) {
      failures += 1;
      if (failures > 3) throw new Error("Lost connection to the local API before the pipeline finished.");
      await wait(1500);
    }
  }
}

const SETTINGS_KEY = "frameforge.settings";
export const loadSettings = () => { try { return { models: {}, enabled: {}, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") }; } catch { return { models: {}, enabled: {} }; } };
export const saveSettings = (settings) => localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));

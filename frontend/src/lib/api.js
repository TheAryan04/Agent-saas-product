export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const AGENTS = ["Orchestrator", "Planner", "Copywriter", "Designer", "Director", "Critic"];
export const OPTIONAL_AGENTS = ["Designer", "Director", "Critic"];
export const TEMPLATES = ["TextReveal", "Flowchart", "SocialMockup", "SearchBar", "DeviceMockup", "CallToAction"];
export const MODELS = ["qwen2.5-coder:3b", "qwen2.5:3b", "llama3.2:3b"];

export async function streamSSE(path, body, onEvent) {
  const response = await fetch(`${API}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail = data.detail;
    const message = typeof detail === "string" ? detail : [detail?.message, ...(detail?.errors || [])].filter(Boolean).join(" — ");
    throw new Error(message || `Request failed (${response.status})`);
  }
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

const SETTINGS_KEY = "frameforge.settings";
export const loadSettings = () => { try { return { models: {}, enabled: {}, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) || "{}") }; } catch { return { models: {}, enabled: {} }; } };
export const saveSettings = (settings) => localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));

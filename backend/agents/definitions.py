import json
from typing import Any, Callable, Dict, Optional, Type

from pydantic import BaseModel

from .schemas import CopywriterOut, CriticOut, DesignerOut, DirectorOut, OrchestratorOut, PlannerOut, TEMPLATES

AGENTS = ["Orchestrator", "Planner", "Copywriter", "Designer", "Director", "Critic"]
OPTIONAL_AGENTS = {"Designer", "Director", "Critic"}

SYSTEM = "You are {name}, one agent in a motion-graphics video pipeline for fictional SaaS/product brands. {role} Never use real brand names or trademarks. Reply with JSON only, matching the schema."

ROLES: Dict[str, str] = {
    "Orchestrator": "Read the brief and extract the product name (invent a short fictional one if missing), audience, tone, one key message, and a scene count of 3-6.",
    "Planner": f"Plan exactly sceneCount scenes. Each picks one template from {TEMPLATES}, a purpose and durationSec 1.5-6. Start with TextReveal, end with CallToAction, avoid repeating templates back to back.",
    "Copywriter": "Write on-screen copy for every planned scene, same count and order. Headlines max 6 words. Flowchart needs 3 short steps, SearchBar needs a query, SocialMockup needs a post, DeviceMockup needs a label, CallToAction needs a button. voiceover is one short spoken sentence per scene.",
    "Designer": "Pick a brand palette as #RRGGBB hex: a vivid primaryColor, a contrasting accentColor, and a dark background. Pick a font from the allowed list.",
    "Director": "Direct motion for every scene, same count and order: a transition, a motion style and a final durationSec 1.5-6 that leaves time to read the copy.",
    "Critic": "Review the assembled scenes for clarity, length and consistency. approved=true if good. Suggest at most 4 small fixes, each targeting a sceneIndex and one field.",
}

SCHEMAS: Dict[str, Type[BaseModel]] = {
    "Orchestrator": OrchestratorOut, "Planner": PlannerOut, "Copywriter": CopywriterOut,
    "Designer": DesignerOut, "Director": DirectorOut, "Critic": CriticOut,
}

CONTEXT_KEYS = {
    "Orchestrator": [], "Planner": ["Orchestrator"], "Copywriter": ["Orchestrator", "Planner"],
    "Designer": ["Orchestrator"], "Director": ["Planner", "Copywriter"], "Critic": [],
}


def scene_count_check(outputs: Dict[str, Any], step) -> Optional[Callable[[Any], None]]:
    targets = [a for a in step if a in ("Copywriter", "Director")]
    if not targets or "Planner" not in outputs:
        return None
    expected = len(outputs["Planner"]["scenes"])

    def check(result):
        for agent in targets:
            part = result if len(step) == 1 else getattr(result, agent)
            if len(part.scenes) != expected:
                raise ValueError(f"{agent}.scenes must have exactly {expected} items, one per planned scene")
    return check


def user_prompt(agent: str, brief: str, outputs: Dict[str, Any], draft: Optional[Dict[str, Any]] = None) -> str:
    parts = [f"BRIEF:\n{brief}"]
    for key in CONTEXT_KEYS[agent]:
        if key in outputs:
            parts.append(f"{key.upper()} OUTPUT:\n{json.dumps(outputs[key])}")
    if agent == "Critic" and draft:
        slim = [{"i": i, "template": s["template"], **{k: s["props"].get(k, "") for k in ("headline", "subline", "eyebrow", "button")}} for i, s in enumerate(draft["scenes"])]
        parts.append(f"ASSEMBLED SCENES:\n{json.dumps(slim)}")
    return "\n\n".join(parts)


def system_prompt(agents) -> str:
    if len(agents) == 1:
        return SYSTEM.format(name=agents[0], role=ROLES[agents[0]])
    roles = " ".join(f"[{a}] {ROLES[a]}" for a in agents)
    return SYSTEM.format(name=" + ".join(agents), role=f"You perform several roles at once and return one key per role. {roles}")

import hashlib
from typing import Any, Dict

FAST_TEMPLATES = ["TextReveal", "DeviceMockup", "CallToAction"]
PALETTES = [
    {"primaryColor": "#7CFFCB", "accentColor": "#55D6FF", "background": "#0B1016", "font": "Outfit"},
    {"primaryColor": "#FFB86B", "accentColor": "#FFE3B3", "background": "#140E0A", "font": "Sora"},
    {"primaryColor": "#8FB8FF", "accentColor": "#C9B8FF", "background": "#0A0D18", "font": "Manrope"},
    {"primaryColor": "#F7FF7C", "accentColor": "#9CF5E0", "background": "#0E0F0A", "font": "Space Mono"},
    {"primaryColor": "#FF8FA3", "accentColor": "#FFD1DA", "background": "#160A0E", "font": "IBM Plex Sans"},
]
TRANSITIONS = ["fade", "slide", "zoom", "wipe"]
MOTION = {"TextReveal": "rise", "Flowchart": "pop", "SocialMockup": "rise", "SearchBar": "type", "DeviceMockup": "drift", "CallToAction": "pop"}


def planner(_: Dict[str, Any]) -> Dict[str, Any]:
    purposes = ["Introduce the product and promise", "Show the product in action", "Close with a clear call to action"]
    return {"scenes": [{"template": t, "purpose": p, "durationSec": 3.0} for t, p in zip(FAST_TEMPLATES, purposes)]}


def designer(outputs: Dict[str, Any]) -> Dict[str, Any]:
    name = outputs.get("Orchestrator", {}).get("productName", "product")
    return dict(PALETTES[int(hashlib.md5(name.lower().encode()).hexdigest(), 16) % len(PALETTES)])


def director(outputs: Dict[str, Any]) -> Dict[str, Any]:
    scenes = []
    for i, (planned, copy) in enumerate(zip(outputs["Planner"]["scenes"], outputs["Copywriter"]["scenes"])):
        words = len(f"{copy.get('headline', '')} {copy.get('subline', '')} {copy.get('detail', '')}".split())
        scenes.append({"transition": TRANSITIONS[i % 4], "motion": MOTION[planned["template"]], "durationSec": round(min(6.0, max(2.5, 1.6 + words * 0.22)), 1)})
    return {"pacing": "rule-based (fast mode)", "scenes": scenes}


RULE_AGENTS = {"Planner": planner, "Designer": designer, "Director": director}

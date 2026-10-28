from typing import Any, Dict, List, Tuple

HEADLINE = "#F4F7F6"
BUTTON_TEXT = "#06110D"
RULES = [("headline", "background", 4.5), ("primaryColor", "background", 3.0), ("accentColor", "background", 4.5), ("button", "primaryColor", 4.5)]


def _rgb(hex_color: str) -> Tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _hex(rgb) -> str:
    return "#" + "".join(f"{round(max(0, min(1, c)) * 255):02X}" for c in rgb)


def luminance(hex_color: str) -> float:
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in _rgb(hex_color)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def _mix(color: str, target: str, t: float) -> str:
    return _hex([c + (d - c) * t for c, d in zip(_rgb(color), _rgb(target))])


def _push(color: str, other: str, need: float, toward: str) -> str:
    for step in range(1, 21):
        candidate = _mix(color, toward, step / 20)
        if ratio(candidate, other) >= need:
            return candidate
    return toward


def audit(brand: Dict[str, Any]) -> Tuple[List[str], Dict[str, str]]:
    """Returns readable issues and a corrected palette (unchanged when everything passes)."""
    fixed = {k: brand[k] for k in ("primaryColor", "accentColor", "background")}
    issues = []
    for fg, bg, need in RULES:
        colors = {"headline": HEADLINE, "button": BUTTON_TEXT, **fixed}
        value = ratio(colors[fg], colors[bg])
        if value >= need:
            continue
        label = {"headline": "White headline text", "primaryColor": "Highlighted headline word", "accentColor": "Eyebrow text", "button": "Button label"}[fg]
        issues.append(f"Rejected colours: {label} on {bg} is {value}:1, needs {need}:1")
        if fg == "headline":
            fixed["background"] = _push(fixed["background"], HEADLINE, need, "#000000")
        elif fg == "button":
            fixed["primaryColor"] = _push(fixed["primaryColor"], BUTTON_TEXT, need, "#FFFFFF")
        else:
            fixed[fg] = _push(fixed[fg], fixed["background"], need, "#FFFFFF")
    return issues, fixed

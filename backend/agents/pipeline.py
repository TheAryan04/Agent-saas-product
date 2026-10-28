import time
from typing import Any, AsyncIterator, Dict, List, Optional

from pydantic import create_model

from . import contrast, ollama
from .definitions import AGENTS, DETAIL, FAST_LLM_SCHEMAS, LLM_SCHEMAS, OPTIONAL_AGENTS, SCHEMAS, scene_count_check, system_prompt, user_prompt
from .rules import RULE_AGENTS
from .schemas import SceneProject

LIMITS = {"eyebrow": 32, "button": 32, "query": 60, "label": 48, "post": 180, "headline": 70, "subline": 140}

FAST_STEPS = [["Planner"], ["Orchestrator", "Copywriter"], ["Designer"], ["Director"]]
DEFAULT_DESIGN = {"primaryColor": "#7CFFCB", "accentColor": "#55D6FF", "background": "#0B1016", "font": "Outfit"}


def assemble(outputs: Dict[str, Any], aspect_ratio: str) -> Dict[str, Any]:
    orch, plan, copy = outputs["Orchestrator"], outputs["Planner"], outputs["Copywriter"]
    design = {**DEFAULT_DESIGN, **(outputs.get("Designer") or {})}
    direct = (outputs.get("Director") or {}).get("scenes", [])
    scenes = []
    for i, planned in enumerate(plan["scenes"]):
        text = copy["scenes"][i] if i < len(copy["scenes"]) else {"headline": planned["purpose"][:60]}
        motion = direct[i] if i < len(direct) else {"transition": "fade", "motion": "rise", "durationSec": planned["durationSec"]}
        props = {k: v for k, v in text.items() if v not in ("", [], None) and k != "detail"}
        key = DETAIL[planned["template"]][0]
        detail = text.get("detail", "")
        if key == "label" and (not detail or "name.app" in detail or not detail.lower().startswith(orch["productName"].lower()[:3])):
            detail = f"{orch['productName'].lower().replace(' ', '')}.app/overview"
        if detail:
            props[key] = detail[:LIMITS.get(key, 180)]
        props.update(transition=motion["transition"], motion=motion["motion"])
        scenes.append({"template": planned["template"], "durationSec": round(float(motion["durationSec"]), 1), "props": props})
    project = {"title": copy["title"], "aspectRatio": aspect_ratio, "brand": {"name": orch["productName"], **design}, "scenes": scenes}
    return SceneProject.model_validate(project).model_dump(exclude_none=True)


TEMPLATE_FIELDS = {"TextReveal": {"eyebrow"}, "Flowchart": {"eyebrow"}, "CallToAction": {"button"}}


def apply_fixes(project: Dict[str, Any], critic: Dict[str, Any]) -> Dict[str, Any]:
    for fix in critic.get("fixes", []):
        if fix["sceneIndex"] >= len(project["scenes"]) or len(fix["value"]) > LIMITS.get(fix["field"], 70):
            continue
        scene = project["scenes"][fix["sceneIndex"]]
        if fix["field"] in {"headline", "subline"} | TEMPLATE_FIELDS.get(scene["template"], set()):
            scene["props"][fix["field"]] = fix["value"]
    return project


def evt(**kwargs) -> Dict[str, Any]:
    return kwargs


def rule_step(agent: str, outputs: Dict[str, Any]) -> Dict[str, Any]:
    return SCHEMAS[agent].model_validate(RULE_AGENTS[agent](outputs)).model_dump()


def critic_contrast(result: Dict[str, Any], draft: Dict[str, Any]) -> Dict[str, Any]:
    issues, fixed = contrast.audit(draft["brand"])
    result["contrast"] = {"passed": not issues, "palette": fixed}
    if issues:
        result["approved"] = False
        result["issues"] = (issues + result.get("issues", []))[:12]
    return result


def finalize(outputs: Dict[str, Any], aspect_ratio: str) -> Dict[str, Any]:
    project = assemble(outputs, aspect_ratio)
    if outputs.get("Critic"):
        project = apply_fixes(project, outputs["Critic"])
    issues, fixed = contrast.audit(project["brand"])
    if issues:
        project["brand"].update(fixed)
    return project


def plan_steps(fast_mode: bool, start_after: Optional[str], enabled: Dict[str, bool]) -> List[List[str]]:
    if start_after:
        steps = [[a] for a in AGENTS[AGENTS.index(start_after) + 1:]]
    else:
        steps = FAST_STEPS if fast_mode else [[a] for a in AGENTS]
    steps = [[a for a in step if enabled.get(a, True) or a not in OPTIONAL_AGENTS] for step in steps]
    return [step for step in steps if step]


async def run(brief: str, aspect_ratio: str, fast_mode: bool = False, models: Optional[Dict[str, str]] = None,
              enabled: Optional[Dict[str, bool]] = None, outputs: Optional[Dict[str, Any]] = None,
              start_after: Optional[str] = None) -> AsyncIterator[Dict[str, Any]]:
    models, enabled, outputs = models or {}, enabled or {}, dict(outputs or {})
    status = await ollama.health()
    if not status["running"]:
        yield evt(type="error", code="ollama_offline", message="Ollama is offline. Start it on this machine, then generate again.", fix=status["fix"])
        return

    fast = fast_mode and not start_after
    steps = plan_steps(fast_mode, start_after, enabled)
    for agent in [a for step in steps for a in step]:
        outputs.pop(agent, None)
    llm_schemas = FAST_LLM_SCHEMAS if fast else LLM_SCHEMAS

    started = time.perf_counter()
    for index, step in enumerate(steps):
        name = " + ".join(step)
        if fast and step[0] in RULE_AGENTS:
            yield evt(type="agent", name=name, agents=step, status="running", index=index, model="rules")
            outputs[step[0]] = rule_step(step[0], outputs)
            yield evt(type="agent", name=name, agents=step, status="done", mode="rules", elapsed=round(time.perf_counter() - started, 2), output=outputs[step[0]])
            continue
        model = models.get(step[0]) or ollama.DEFAULT_MODEL
        yield evt(type="agent", name=name, agents=step, status="running", index=index, model=model)
        draft = assemble(outputs, aspect_ratio) if "Critic" in step else None
        out_model = llm_schemas[step[0]] if len(step) == 1 else create_model("Merged", **{a: (llm_schemas[a], ...) for a in step})
        try:
            async for item in ollama.structured(model, system_prompt(step), user_prompt(step, brief, outputs, draft), out_model, scene_count_check(outputs, step)):
                if "token" in item:
                    yield evt(type="token", name=name, text=item["token"])
                elif "retry" in item:
                    yield evt(type="agent", name=name, agents=step, status="retry", error=item["retry"])
                else:
                    result = item["result"].model_dump()
                    outputs.update({step[0]: result} if len(step) == 1 else result)
        except ollama.OllamaOffline:
            yield evt(type="error", code="ollama_offline", message="Lost connection to Ollama.", fix=status["fix"])
            return
        except ollama.AgentFailed as exc:
            yield evt(type="agent", name=name, agents=step, status="error", error=str(exc))
            yield evt(type="error", code="agent_failed", agent=name, message=str(exc))
            return
        if fast and "Copywriter" in step:
            outputs["Copywriter"]["scenes"] = [{**s, "steps": [], "voiceover": ""} for s in outputs["Copywriter"]["scenes"]]
            outputs["Orchestrator"]["sceneCount"] = len(outputs["Planner"]["scenes"])
        if "Critic" in step:
            outputs["Critic"] = critic_contrast(outputs["Critic"], draft)
        yield evt(type="agent", name=name, agents=step, status="done", elapsed=round(time.perf_counter() - started, 2),
                  output={a: outputs[a] for a in step} if len(step) > 1 else outputs[step[0]])

    try:
        project = finalize(outputs, aspect_ratio)
    except Exception as exc:
        yield evt(type="error", code="assemble_failed", message=f"Could not assemble scenes: {exc}")
        return
    yield evt(type="complete", project=project, outputs=outputs)


def validate_outputs(outputs: Dict[str, Any], upto: str) -> List[str]:
    errors = []
    for agent in AGENTS[:AGENTS.index(upto) + 1]:
        if agent not in outputs:
            if agent not in OPTIONAL_AGENTS:
                errors.append(f"{agent}: missing output")
            continue
        try:
            outputs[agent] = SCHEMAS[agent].model_validate(outputs[agent]).model_dump()
        except Exception as exc:
            errors.append(f"{agent}: {str(exc)[:300]}")
    return errors

import json
import os
from typing import Any, AsyncIterator, Dict, List, Type

import httpx
from pydantic import BaseModel, ValidationError

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:3b")


class OllamaOffline(Exception):
    pass


class AgentFailed(Exception):
    pass


def inline_schema(model: Type[BaseModel]) -> Dict[str, Any]:
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].split("/")[-1]])
            return {key: walk(value) for key, value in node.items() if not (key == "title" and isinstance(value, str))}
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return walk(schema)


async def health() -> Dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            models = [item.get("name") for item in response.json().get("models", [])]
        return {"running": True, "model": DEFAULT_MODEL, "model_pulled": any(DEFAULT_MODEL in m for m in models), "models": models, "fix": f"ollama pull {DEFAULT_MODEL}"}
    except Exception:
        return {"running": False, "model": DEFAULT_MODEL, "model_pulled": False, "models": [], "fix": f"ollama serve && ollama pull {DEFAULT_MODEL}"}


async def stream_chat(model: str, messages: List[Dict[str, str]], schema: Dict[str, Any]) -> AsyncIterator[str]:
    payload = {"model": model, "messages": messages, "format": schema, "stream": True, "keep_alive": "30m", "options": {"temperature": 0.2, "num_ctx": 4096, "num_predict": 1200}}
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(600, connect=5)) as client:
            async with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
                if response.status_code == 404:
                    raise AgentFailed(f"Model '{model}' is not pulled. Run: ollama pull {model}")
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    if chunk.get("error"):
                        raise AgentFailed(chunk["error"])
                    text = chunk.get("message", {}).get("content", "")
                    if text:
                        yield text
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise OllamaOffline(str(exc)) from exc


GRAMMAR_HEAVY = {"minLength", "maxLength"}


def grammar_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """String length limits explode llama.cpp grammars on CPU; enforce them by clipping instead."""
    if isinstance(schema, dict):
        return {k: grammar_schema(v) for k, v in schema.items() if k not in GRAMMAR_HEAVY}
    if isinstance(schema, list):
        return [grammar_schema(v) for v in schema]
    return schema


def clip(value: Any, schema: Dict[str, Any]) -> Any:
    if isinstance(value, str) and "maxLength" in schema:
        return value[:schema["maxLength"]].strip()
    if isinstance(value, list):
        item_schema = schema.get("items", {})
        return [clip(v, item_schema) for v in value[:schema.get("maxItems", len(value))]]
    if isinstance(value, dict):
        props = schema.get("properties", {})
        return {k: clip(v, props.get(k, {})) for k, v in value.items()}
    return value


async def structured(model: str, system: str, user: str, out: Type[BaseModel], check=None) -> AsyncIterator[Dict[str, Any]]:
    """Yields token/retry events, finally {'result': validated_model}. One retry on validation failure."""
    full_schema = inline_schema(out)
    schema = grammar_schema(full_schema)
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for attempt in range(2):
        text = ""
        async for token in stream_chat(model, messages, schema):
            text += token
            yield {"token": token}
        try:
            result = out.model_validate(clip(json.loads(text), full_schema))
            if check:
                check(result)
            yield {"result": result}
            return
        except (json.JSONDecodeError, ValidationError, ValueError) as exc:
            error = str(exc)[:600]
            if attempt == 1:
                raise AgentFailed(f"Output failed validation after retry: {error}")
            yield {"retry": error}
            messages += [{"role": "assistant", "content": text}, {"role": "user", "content": f"Your JSON failed validation:\n{error}\nReturn the corrected JSON only."}]

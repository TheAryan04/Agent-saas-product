import asyncio
import json
import time
import uuid
from typing import Any, AsyncIterator, Dict, List

TERMINAL = {"complete", "error"}
MAX_RUNS = 12
STREAM_WINDOW_SEC = 40


class Run:
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.done = False
        self.changed = asyncio.Event()

    def push(self, event: Dict[str, Any]):
        self.events.append(event)
        self.changed.set()


class RunStore:
    """Pipeline runs execute in the background; clients (re)connect to read events from an offset."""

    def __init__(self):
        self.runs: Dict[str, Run] = {}
        self.lock = asyncio.Lock()
        self.tasks: set = set()

    def start(self, events: AsyncIterator[Dict[str, Any]]) -> str:
        run_id = str(uuid.uuid4())
        run = self.runs[run_id] = Run()
        for old in list(self.runs)[:-MAX_RUNS]:
            self.runs.pop(old, None)
        task = asyncio.create_task(self._consume(run, events))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return run_id

    async def _consume(self, run: Run, events: AsyncIterator[Dict[str, Any]]):
        if self.lock.locked():
            run.push({"type": "queued", "message": "Waiting for the previous run to finish"})
        async with self.lock:
            try:
                async for event in events:
                    run.push(event)
            except Exception as exc:
                run.push({"type": "error", "code": "pipeline_crashed", "message": str(exc)[:300]})
            finally:
                if not run.events or run.events[-1]["type"] not in TERMINAL:
                    run.push({"type": "error", "code": "pipeline_stopped", "message": "Pipeline stopped unexpectedly"})
                run.done = True
                run.changed.set()

    async def stream(self, run_id: str, after: int) -> AsyncIterator[str]:
        run = self.runs[run_id]
        cursor, started = after, time.monotonic()
        while True:
            while cursor < len(run.events):
                yield f"data: {json.dumps(run.events[cursor], separators=(',', ':'))}\n\n"
                cursor += 1
            if run.done or time.monotonic() - started > STREAM_WINDOW_SEC:
                return
            run.changed.clear()
            try:
                await asyncio.wait_for(run.changed.wait(), timeout=10)
            except asyncio.TimeoutError:
                yield ": keep-alive\n\n"

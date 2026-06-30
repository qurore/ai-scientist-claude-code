"""Shared state/run-directory helpers for the AI-Scientist skills."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "runs"
CACHE = REPO / ".aisci_cache"

STAGES = ["ideate", "experiment", "writeup", "review"]


def _stamp() -> str:
    return time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower()).strip("_")
    return (text or "study")[:48]


def run_dir(run_id: str) -> Path:
    return RUNS / run_id


def state_path(run_id: str) -> Path:
    return run_dir(run_id) / "state.json"


def load_state(run_id: str) -> dict:
    p = state_path(run_id)
    if not p.exists():
        raise FileNotFoundError(f"no state.json for run {run_id!r} ({p})")
    return json.loads(p.read_text())


def save_state(run_id: str, state: dict) -> None:
    state["updated"] = _stamp()
    state_path(run_id).write_text(json.dumps(state, indent=2))


def set_current(run_id: str) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "current_run").write_text(run_id)


def current_run() -> str | None:
    p = CACHE / "current_run"
    if p.exists():
        rid = p.read_text().strip()
        if rid and run_dir(rid).exists():
            return rid
    return None


def new_run(slug: str, topic: str = "") -> str:
    slug = slugify(slug)
    run_id = f"{_stamp()}_{slug}"
    d = run_dir(run_id)
    for sub in ("experiment/code", "experiment/logs",
                "experiment/experiment_results", "experiment/plots",
                "writeup"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    state = {
        "run_id": run_id,
        "slug": slug,
        "topic": topic,
        "stage": "ideate",
        "status": "pending",
        "idea_slug": None,
        "created": _stamp(),
        "updated": _stamp(),
    }
    save_state(run_id, state)
    (d / "study.md").write_text(
        f"# Study: {slug}\n\n- **Run id:** {run_id}\n- **Topic:** {topic}\n\n"
        f"## Log\n\n- {_stamp()} — study created (stage: ideate)\n"
    )
    set_current(run_id)
    return run_id


def append_study_log(run_id: str, line: str) -> None:
    p = run_dir(run_id) / "study.md"
    with p.open("a") as f:
        f.write(f"- {_stamp()} — {line}\n")

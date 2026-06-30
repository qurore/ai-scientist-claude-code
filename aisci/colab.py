"""Colab GPU backend for ``aisci.exec`` — compute only, never an LLM.

The Mac host has no CUDA GPU, so this backend borrows one from Google Colab to run
*experiment code* (model building, training, evaluation). The intelligence of the
pipeline (ideation, writing, review) stays with the Claude Code agent — we never
call ``google-colab-ai`` / Gemini or any external LLM.

Mechanism: a plain shared folder, no Google API / OAuth code.
  1. ``run_colab`` writes a job (the experiment ``code/`` + ``job.json``) into
     ``$AISCI_COLAB_SYNC/jobs/<job_id>/`` and touches a ``READY`` marker last.
  2. A long-running runner notebook on Colab (``colab/colab_runner.ipynb``) mounts
     the *same* Drive folder, executes the script on the GPU, and writes results +
     a ``DONE`` marker into ``$AISCI_COLAB_SYNC/results/<job_id>/``.
  3. ``run_colab`` polls for ``DONE``, copies the log / ``experiment_results`` /
     ``plots`` back into the local run dir, and returns the same record schema as
     the local backend.

``$AISCI_COLAB_SYNC`` is the *local* mirror (e.g. via Google Drive for Desktop) of
the Drive folder the notebook mounts — typically ``My Drive/aisci-colab``.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from . import state


def _sync_root() -> Path | None:
    root = os.environ.get("AISCI_COLAB_SYNC")
    if not root:
        return None
    return Path(root).expanduser()


def _err_record(exp: Path, run_id: str, node: str, seed: int | None, msg: str) -> dict:
    """Write a buggy record (+ a log explaining why) so callers get clean JSON."""
    log_path = exp / "logs" / f"{node}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(f"# colab backend error\n{msg}\n")
    rec = {
        "node": node,
        "ok": False,
        "is_buggy": True,
        "returncode": -1,
        "timed_out": False,
        "duration_s": 0.0,
        "metric": None,
        "seed": seed,
        "log": str(log_path.relative_to(state.run_dir(run_id))),
        "stderr_tail": msg[-800:],
        "backend": "colab",
    }
    rp = exp / "experiment_results" / f"{node}.json"
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text(json.dumps(rec, indent=2))
    return rec


def run_colab(run_id: str, exp: Path, script_rel: str, node: str,
              timeout: int, seed: int | None) -> dict:
    """Submit a job to the Colab runner over Drive and pull the results back."""
    root = _sync_root()
    if root is None or not root.exists():
        return _err_record(
            exp, run_id, node, seed,
            "AISCI_COLAB_SYNC is not set or does not exist. Point it at your local "
            "Google Drive mirror of 'My Drive/aisci-colab' — the same folder the "
            "Colab runner notebook mounts. See colab/README.md.",
        )

    code_dir = exp / "code"
    if not code_dir.exists():
        return _err_record(exp, run_id, node, seed,
                           f"expected experiment code dir at {code_dir}")

    job_id = f"{run_id}__{node}__{int(time.time())}"
    jobs = root / "jobs" / job_id
    results = root / "results" / job_id
    jobs.mkdir(parents=True, exist_ok=True)

    # Bundle the experiment code (scripts are expected to generate their own
    # small/synthetic data, per the repo's reality checks — we don't ship datasets).
    dst = jobs / "code"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(code_dir, dst)
    (jobs / "job.json").write_text(json.dumps({
        "job_id": job_id,
        "project_id": run_id,
        "node": node,
        "script": script_rel,
        "timeout": timeout,
        "seed": seed,
        "created": time.time(),
    }, indent=2))
    (jobs / "READY").write_text(str(time.time()))  # written last → atomic-ish handoff

    poll = int(os.environ.get("AISCI_COLAB_POLL", "10"))
    extra = int(os.environ.get("AISCI_COLAB_WAIT", "1800"))
    deadline = time.time() + timeout + extra
    done = results / "DONE"
    while time.time() < deadline:
        if done.exists():
            break
        time.sleep(poll)

    if not done.exists():
        return _err_record(
            exp, run_id, node, seed,
            f"No result from Colab within {timeout + extra}s. Is the runner notebook "
            f"running on a GPU runtime and watching {root}/jobs? job_id={job_id}",
        )

    # Pull artifacts back into the local run dir (identical layout to local backend).
    (exp / "logs").mkdir(parents=True, exist_ok=True)
    (exp / "experiment_results").mkdir(parents=True, exist_ok=True)
    src_log = results / "logs" / f"{node}.log"
    if src_log.exists():
        shutil.copy(src_log, exp / "logs" / f"{node}.log")
    for f in (results / "experiment_results").glob("*"):
        if f.is_file():
            shutil.copy(f, exp / "experiment_results" / f.name)
    pdir = results / "plots"
    if pdir.exists():
        (exp / "plots").mkdir(parents=True, exist_ok=True)
        for f in pdir.glob("*"):
            if f.is_file():
                shutil.copy(f, exp / "plots" / f.name)

    rp = exp / "experiment_results" / f"{node}.json"
    try:
        rec = json.loads(rp.read_text())
    except Exception:
        return _err_record(exp, run_id, node, seed,
                           f"colab result record missing/corrupt at {rp} (job_id={job_id})")

    # The local run dir is authoritative for the log path; tag the backend.
    rec["log"] = f"experiment/logs/{node}.log"
    rec["backend"] = "colab"
    rp.write_text(json.dumps(rec, indent=2))
    return rec

"""Execute an experiment script inside a run's experiment dir with capture + timeout.

    python -m aisci.exec <run_id|runs/run_id> <script-rel-to-experiment> [--timeout S] [--seed N]

The script is run with cwd = ``runs/<id>/experiment`` so it can read/write only
within the sandboxed run directory. stdout+stderr go to ``logs/<node>.log``. A
metric is captured from either:
  * a JSON line on stdout containing a ``"metric"`` key, or
  * a file ``experiment_results/<node>.json`` the script writes itself.
A merged record is written to ``experiment_results/<node>.json`` and a one-line
JSON summary is printed (so the calling skill can read it back).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from . import state


def _find_metric_in_stdout(text: str) -> dict | None:
    found = None
    for line in text.splitlines():
        line = line.strip()
        if not (line.startswith("{") and line.endswith("}")):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "metric" in obj:
            found = obj  # keep the last metric line
    return found


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aisci.exec")
    p.add_argument("run", help="run id or runs/<id>")
    p.add_argument("script", help="script path relative to the experiment dir, e.g. code/n3.py")
    p.add_argument("--timeout", type=int, default=1800)
    p.add_argument("--seed", type=int, default=None)
    args = p.parse_args(argv)

    run_id = Path(args.run).name
    exp = state.run_dir(run_id) / "experiment"
    if not exp.exists():
        print(json.dumps({"ok": False, "error": f"experiment dir missing for run {run_id}"}))
        return 2

    script = (exp / args.script).resolve()
    if not script.exists() or exp not in script.parents:
        print(json.dumps({"ok": False, "error": f"script must live under {exp}"}))
        return 2

    node = script.stem
    log_path = exp / "logs" / f"{node}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    results_path = exp / "experiment_results" / f"{node}.json"

    env = dict(os.environ)
    if args.seed is not None:
        env["AISCI_SEED"] = str(args.seed)
    # Discourage accidental large downloads / network from inside experiments.
    env.setdefault("HF_HUB_OFFLINE", "0")  # leave configurable; skills decide

    t0 = time.time()
    timed_out = False
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(exp),
            env=env,
            capture_output=True,
            text=True,
            timeout=args.timeout,
        )
        rc = proc.returncode
        out, err = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as e:
        timed_out = True
        rc = -1
        out = e.stdout or ""
        err = (e.stderr or "") + f"\n[aisci.exec] TIMEOUT after {args.timeout}s"
    dur = time.time() - t0

    with log_path.open("w") as f:
        f.write(f"$ {sys.executable} {script}\n# cwd={exp}\n# rc={rc} dur={dur:.1f}s\n")
        f.write("\n----- STDOUT -----\n")
        f.write(out or "")
        f.write("\n----- STDERR -----\n")
        f.write(err or "")

    metric = _find_metric_in_stdout(out or "")
    if metric is None and results_path.exists():
        try:
            metric = json.loads(results_path.read_text())
        except json.JSONDecodeError:
            metric = None

    is_buggy = rc != 0 or timed_out or metric is None
    record = {
        "node": node,
        "ok": not is_buggy,
        "is_buggy": is_buggy,
        "returncode": rc,
        "timed_out": timed_out,
        "duration_s": round(dur, 1),
        "metric": metric,
        "seed": args.seed,
        "log": str(log_path.relative_to(state.run_dir(run_id))),
        "stderr_tail": (err or "")[-800:],
    }
    results_path.write_text(json.dumps(record, indent=2))
    print(json.dumps(record))
    return 0 if not is_buggy else 1


if __name__ == "__main__":
    raise SystemExit(main())

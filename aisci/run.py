"""CLI for managing AI-Scientist study runs.

    python -m aisci.run new   --slug my_study --topic "research topic"
    python -m aisci.run show  [--run <id>]
    python -m aisci.run set   --stage experiment --status done [--idea-slug foo] [--run <id>]
    python -m aisci.run list
"""

from __future__ import annotations

import argparse
import json
import sys

from . import state


def _resolve(run_id: str | None) -> str:
    rid = run_id or state.current_run()
    if not rid:
        print("no run specified and no current run set", file=sys.stderr)
        raise SystemExit(2)
    return rid


def cmd_new(args) -> int:
    rid = state.new_run(args.slug, args.topic or "")
    print(rid)
    return 0


def cmd_show(args) -> int:
    rid = _resolve(args.run)
    print(json.dumps(state.load_state(rid), indent=2))
    return 0


def cmd_set(args) -> int:
    rid = _resolve(args.run)
    st = state.load_state(rid)
    if args.stage:
        st["stage"] = args.stage
    if args.status:
        st["status"] = args.status
    if args.idea_slug:
        st["idea_slug"] = args.idea_slug
    if args.complete:
        st["status"] = "complete"
    state.save_state(rid, st)
    if args.note:
        state.append_study_log(rid, args.note)
    print(json.dumps(st, indent=2))
    return 0


def cmd_list(args) -> int:
    if not state.RUNS.exists():
        return 0
    for d in sorted(state.RUNS.iterdir()):
        sp = d / "state.json"
        if sp.exists():
            st = json.loads(sp.read_text())
            cur = " *" if st["run_id"] == state.current_run() else "  "
            print(f"{cur} {st['run_id']:40s} stage={st['stage']:10s} status={st['status']}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aisci.run")
    sub = p.add_subparsers(dest="cmd", required=True)

    pn = sub.add_parser("new")
    pn.add_argument("--slug", required=True)
    pn.add_argument("--topic", default="")
    pn.set_defaults(func=cmd_new)

    ps = sub.add_parser("show")
    ps.add_argument("--run", default=None)
    ps.set_defaults(func=cmd_show)

    pset = sub.add_parser("set")
    pset.add_argument("--run", default=None)
    pset.add_argument("--stage", choices=state.STAGES, default=None)
    pset.add_argument("--status", default=None)
    pset.add_argument("--idea-slug", dest="idea_slug", default=None)
    pset.add_argument("--complete", action="store_true")
    pset.add_argument("--note", default=None)
    pset.set_defaults(func=cmd_set)

    pl = sub.add_parser("list")
    pl.set_defaults(func=cmd_list)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

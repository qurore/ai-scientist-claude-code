# AI-Scientist on Claude Code

This repo runs **Sakana AI's AI-Scientist-v2 pipeline entirely inside Claude Code**,
using the Claude Code ecosystem natively: **Skills** are the pipeline stages and
**Hooks** are the automation + safety layer. **You (the Claude Code agent) are the
scientist** — you generate ideas, write & run experiment code, write the paper, and
review it, with your own tools. No external LLM API keys are used.

## Architecture (two layers)

1. **Native layer (primary)** — `.claude/skills/` + `.claude/hooks/`.
   The pipeline is driven by Claude Code itself. This is the intended way to operate.
2. **Bridge layer (optional adapter)** — `bridge/`.
   Routes the *unmodified upstream* Python's LLM/VLM/tree-search calls to the `claude`
   CLI in headless mode (`claude -p`), so any upstream stage can run "on Claude Code
   only". Use it only when you want strict upstream parity for a stage.

## Repo layout

```
.claude/skills/        ai-scientist (orchestrator) + ideate/experiment/writeup/review
.claude/hooks/         session_start, guard_experiment_exec, log_tool_use, stop_autopilot
.claude/settings.json  wires the hooks; default-off autopilot; minimal permissions
aisci/                 thin python helpers the skills shell out to (run/exec/latex/state)
bridge/                claude -p adapter (claude_cli, model_map, *_backend, install, run)
config/model_map.json  upstream-model -> Claude-model overrides
scripts/setup.sh       idempotent env setup (clones vendor, builds .venv, installs deps)
scripts/doctor.sh      environment diagnostics
ideas/                 topic descriptions (input to ideation); TEMPLATE_topic.md
runs/<id>/             one directory per study (gitignored) — see below
vendor/AI-Scientist-v2 upstream clone (gitignored) — the reference spec
```

A study lives entirely under `runs/<YYYY-MM-DD_HH-MM-SS>_<slug>/`:
`state.json` (source of truth), `idea.{md,json}`, `experiment/` (code, logs,
experiment_results, plots, journal.jsonl), `writeup/` (latex, paper.pdf),
`review.json`, `study.md` (lab notebook).

## How to operate

- Start / coordinate a study with the **`ai-scientist`** skill. Run stages with
  `/ai-scientist-ideate` → `/ai-scientist-experiment` → `/ai-scientist-writeup` →
  `/ai-scientist-review`. Each skill's SKILL.md is the authoritative procedure.
- Keep `runs/<id>/state.json` and `study.md` current after every stage (the helpers do
  this: `aisci.run set ...`). State is what makes a study resumable and drives autopilot.
- The SessionStart hook prints an env banner each session. If something's missing it
  tells you to run `scripts/setup.sh`.

### Helper commands (run from repo root)
```bash
.venv/bin/python -m aisci.run new --slug <slug> --topic "<topic>"   # create a run
.venv/bin/python -m aisci.run show|list|set ...                     # inspect/update state
.venv/bin/python -m aisci.exec runs/<id> code/<file>.py --timeout S # run an experiment script
.venv/bin/python -m aisci.latex runs/<id>/writeup/latex paper.tex   # compile the paper
bash scripts/doctor.sh                                              # diagnose env
```

### Bridge usage (only for upstream parity)
```bash
python -m bridge.run vendor/AI-Scientist-v2/<script>.py [args...]
```
`bridge.install()` swaps `ai_scientist.llm`, `ai_scientist.vlm`, and
`ai_scientist.treesearch.backend.query` for Claude-Code-backed equivalents. Model names
map by tier (see `bridge/model_map.py`, override in `config/model_map.json`).

## Safety (enforced by the PreToolUse guard)

The upstream README warns that LLM-written code is dangerous. The
`guard_experiment_exec` hook **denies** destructive/exfil/sandbox-escape shell
(`rm -rf /`, `curl|sh`, `sudo`, credential reads, guard tampering, …) and is neutral
otherwise. **Never route around a block** — redesign the experiment to stay inside the
run dir. All experiment I/O must live under `runs/<id>/experiment/`.

## Reality checks

- **No CUDA GPU** here (macOS). Keep experiments tiny: synthetic/small data, small
  models, CPU/MPS, short training. Be honest with the user about scope for big ideas.
- **Never fabricate** results or citations. Every number in a paper must trace to a file
  in `experiment/`; every citation must be a real, findable paper. Report failures
  honestly (the default `icbinb` venue is for "not better" results).
- **Cost:** every stage spends Claude Code tokens. Bridge calls are logged to
  `.aisci_cache/bridge_calls.jsonl`; summarize spend when a study finishes.

## Autopilot (opt-in)

Default: pause between stages for user review. Set `AISCI_AUTOPILOT=1` to let the Stop
hook auto-advance stages (bounded by `AISCI_AUTOPILOT_MAX`, default 8). Tell the user
this toggle exists; don't enable it silently.

## Conventions

- Python: match upstream style; helpers in `aisci/` stay thin (mechanics only — the
  intelligence is in the skills/you).
- Don't commit `vendor/`, `.venv/`, `runs/`, or secrets (see `.gitignore`).
- When unsure how a stage should behave, **read the upstream reference** named in that
  stage's SKILL.md and follow it.
```

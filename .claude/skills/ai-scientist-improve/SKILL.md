---
name: ai-scientist-improve
description: Stage 5 (optional loop) of the AI Scientist pipeline — iteratively raise a paper's quality on the SAME theme by acting on its peer review (run stronger experiments, rewrite), then re-reviewing, until the honest Overall score clears a target (default 8/10) or an iteration cap is hit. Use after a study has a review.json and the user wants to push the score up.
---

# Stage 5 — Improvement loop (review → revise → re-review)

Take an existing study and make it **genuinely better** on the same theme until an honest
review clears the target score. This is the mechanism that turns a first draft into a
strong paper.

## Target and bound
- **Target:** Overall ≥ `AISCI_IMPROVE_TARGET` (default **8/10**).
- **Bound:** at most `AISCI_IMPROVE_MAX_ITERS` iterations (default **4**) so cost is finite.
- Calibration: a strong paper *accepted* to the ICLR 2025 ICBINB workshop averaged ~6.3/10.
  Clear that floor and aim for ≥ 8 — but only by being genuinely better.

## Integrity (read this first — it is the whole point)
- **The score must rise through real improvement, never through a more lenient review.**
  Re-review with the *same* critical standard as `/ai-scientist-review` every time. Do not
  nudge numbers to "reach" the target.
- **No fabrication.** Every new number still traces to a file in `experiment/`; every new
  citation is real. New experiments are really run via `aisci.exec`.
- **Blind re-review — no leakage to the grader.** The re-review must judge the paper *on its
  merits only*. The reviewer is given **only** the paper PDF + `experiment_results/` (to
  verify numbers) — **never** the iteration number, the fact that this is a revision, the
  prior reviews, or any prior score. The paper must carry **no revision markers** (no "v2",
  "revised", "iteration k", changelog, or "response to reviewers"). Keep the `reviews/`
  history, `score_history.jsonl`, and `decisions.jsonl` strictly in the meta layer for the
  human; they are never inputs to the review. This blindness is what makes a rising score
  meaningful rather than anchoring/leniency bias.
- **Honest ceiling.** If, after real changes, the honest score plateaus below target, stop
  and say so plainly: report the current honest score and exactly what would be needed to
  go higher (usually scale/compute beyond this laptop). A truthful 6.5 beats a fake 8.

## Human-idea inbox (read at the START of every iteration)
Each project has an inbox `projects/<id>/human_ideas.md` where a person can drop a hypothesis
or "try this" at ANY time, even mid-study. At the start of every iteration, **before** acting
on the review:
1. `aisci.run ideas --run <id>` lists the OPEN entries (unchecked `[ ]`).
2. Fold each open idea into this iteration's plan as an explicit hypothesis to test, alongside
   the review-driven work, and run real experiments for it (`aisci.exec`).
3. **Close it with the honest outcome** so it is never re-read or re-tested:
   `aisci.run idea-resolve --run <id> --id N --outcome confirmed|refuted|inconclusive --note "<what you did, the result, the evidence file>"`.
   A *confirmed* idea should be reflected in the paper; a *refuted* one stays closed with its
   result, so later iterations are not pulled back toward a hypothesis already shown wrong.
   Log a `aisci.run decide ...` for any idea that materially shaped the work.

This is enforced-by-convention via the helper (it flips `[ ]`→`[x]` and appends a `**Tested**`
annotation); never hand-edit the checkboxes. Human ideas are tested with the same rigor and
honesty as everything else — confirm only what the experiments support.

## Procedure (one iteration)
0. **Consult the human-idea inbox** (above) and merge any open ideas into the plan.
1. **Read the latest review** `projects/<id>/review.json`. Rank its Weaknesses/Questions by
   how much each holds down Overall and the sub-scores (Soundness, Significance, Quality,
   Clarity, Contribution).
2. **Plan the highest-leverage revisions.** Map each weakness to a concrete action:
   - Soundness/Significance/Quality → **new or stronger experiments** (Stage 2): broaden
     conditions (e.g., more optimizers, architectures, seeds, baselines), add the control
     that removes a confound, sharpen a measurement, add an ablation. Run them with
     `aisci.exec`; update `experiment_results/summary.json` and figures.
   - Clarity/Presentation → **rewrite** (Stage 3): tighten arguments, improve figures and
     captions, expand related work, make claims precise. (No length limit — see the writeup
     skill.)
   - Contribution/Originality → sharpen the framing or add the analysis that makes the
     contribution land.
3. **Record the decisions** (enforced): for each substantive change,
   `aisci.run decide --stage <experiment|writeup> --decision "…" --why "…" --evidence "…"`.
4. **Re-run the affected stage(s)** — regenerate results, plots, and the paper; recompile to
   PDF; re-read it.
5. **Re-review** honestly using the full `/ai-scientist-review` rubric (which does **not**
   penalize length — see that skill). Version the review (see "Versioning" below):
   - before the first revision, copy the existing `review.json` → `reviews/review_000.json`,
   - write the new `review.json` and also save it as `reviews/review_<NNN>.json`,
   - append a line to `reviews/score_history.jsonl`,
   - record the move: `aisci.run decide --stage review --decision "iteration <k>: Overall <old>→<new>" --why "<what changed and why it moved the score>" --evidence "reviews/review_<NNN>.json"`.
6. **Decide to continue or stop.** If Overall ≥ target → stop (success). If iteration cap
   reached → stop (report honest score + gap). Otherwise loop to step 1.

## Versioning — reviews yes, implementation no
- **Reviews are versioned.** Keep the *full* review history so the trajectory is auditable
  — start score → final score, and how many iterations it took to get there:
  - `projects/<id>/reviews/review_000.json` = the **initial** review (copy the existing
    `review.json` here before the first revision),
  - `review_001.json`, `review_002.json`, … = after each iteration,
  - `projects/<id>/review.json` always mirrors the **latest**,
  - `projects/<id>/reviews/score_history.jsonl` = one line per iteration
    `{iter, overall, soundness, significance, clarity, quality, contribution, decision, ts}`
    so the start→final progression and the #iterations-to-target are trivial to read off.
- **Implementation is NOT versioned.** Experiment code, results, and the paper just evolve
  in place (overwrite) — no per-iteration snapshots of code/figures/PDF. The decision log
  (`decisions.jsonl`) records *why* each change was made; that is the implementation's audit
  trail, not file copies.

## State
- Keep `state.json` coherent: while iterating, set `stage` to whatever you're redoing
  (`experiment`/`writeup`) and `status="in_progress"`; after each re-review set
  `stage="review"`, `status="done"`; when the loop ends, `--complete`.
- The append-only `decisions.jsonl` + `study.md` + `reviews/score_history.jsonl` together
  form the score-trajectory log: a human sees iteration-by-iteration what changed and how
  the score moved.

## Output to the user
A short trajectory: starting Overall → each iteration's change and new Overall → final
verdict, with the honest assessment (target met, or the genuine ceiling and what more would
take). Point to `paper.pdf`, `review.json`, and the `reviews/` history.

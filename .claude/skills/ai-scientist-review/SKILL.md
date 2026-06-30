---
name: ai-scientist-review
description: Stage 4 of the AI Scientist pipeline — produce a rigorous NeurIPS-style peer review of the generated paper (text + figures), as a structured JSON verdict. Use after a paper PDF exists, or when the user wants the AI Scientist to review a paper.
---

# Stage 4 — Review

Act as a critical, fair conference reviewer of `projects/<id>/writeup/paper.pdf`. You can
**read the PDF and its figures directly** (Read tool) — use that, plus the underlying
`experiment/` results, to judge whether the paper's claims are actually supported.

## Authoritative reference
- Text review rubric/prompt: `vendor/AI-Scientist-v2/ai_scientist/perform_llm_review.py`
- Figure/caption/reference review: `vendor/AI-Scientist-v2/ai_scientist/perform_vlm_review.py`
Read these to match the exact rubric and scales.

## Review blind — no leakage
Judge the paper **fresh, on its own merits**, from only what is in front of you: the
`paper.pdf` and the `experiment/` results (to verify numbers). You are **not** told — and
must **not** assume or look up — whether this is a first submission or a revision, which
improvement iteration it is, or what any prior review or score said. Do **not** open
`reviews/`, `score_history.jsonl`, or `decisions.jsonl`. This keeps the score an unbiased
function of the paper itself (no anchoring or leniency from "it has improved").

## Procedure
1. **Read the paper.** Open `paper.pdf` with Read (you see text + figures). Also load
   `experiment/experiment_results/summary.json` so you can verify the paper's numbers
   against what was actually measured.
2. **Text review** → produce the JSON below.
3. **Figure/caption/reference check** (mirrors the VLM review): for each figure, confirm
   it renders, the caption matches the content, and it's referenced in the text. Flag
   any figure whose claim isn't supported by `experiment_results/`.
4. **Integrity checks specific to autonomous papers:** flag (a) any number not traceable
   to `experiment/`, (b) any citation you can't verify is a real paper, (c) overclaiming
   beyond the small-scale evidence.

## Review JSON schema (write to `projects/<id>/review.json`)
```json
{
  "Summary": "What the paper does.",
  "Strengths": ["..."],
  "Weaknesses": ["..."],
  "Originality": 3,
  "Quality": 3,
  "Clarity": 3,
  "Significance": 2,
  "Questions": ["..."],
  "Limitations": ["..."],
  "Ethical Concerns": false,
  "Soundness": 3,
  "Presentation": 3,
  "Contribution": 2,
  "Overall": 5,
  "Confidence": 4,
  "Decision": "Reject",
  "Figure_Review": [{"figure":"fig1.png","renders":true,"caption_matches":true,"supported":true,"note":"..."}],
  "Integrity_Flags": ["any unsupported number / unverifiable citation / overclaim"]
}
```
Scales (match upstream): Originality/Quality/Clarity/Significance 1–4; Soundness/
Presentation/Contribution 1–4; Overall 1–10; Confidence 1–5; Decision ∈ {Accept, Reject}.

## Be honest and calibrated
Score against a **high bar** — the standard of a strong paper at a top venue — but score
**honestly**. The point of the review is a *truthful* signal that drives real improvement,
so **never inflate**: a higher score must be earned by a genuinely better paper, not by a
more generous reviewer. Both directions matter — a strong, rigorous, clearly-written study
*can* merit Accept and a high Overall; a thin one should be marked as such with concrete,
actionable weaknesses.

Calibration reference: a strong paper *accepted* to the ICLR 2025 "I Can't Believe It's Not
Better" (ICBINB) workshop averaged ~6.3/10 across three reviewers. Treat that as a floor to
clear, not a ceiling — aim the *work* (not the scoring) at Overall ≥ 8. This skill feeds the
improvement loop (`/ai-scientist-improve`): make the **Weaknesses** and **Questions**
specific and actionable so the next revision can actually close them.

**Do NOT penalize length or format.** This pipeline imposes no page/character limit (see the
writeup skill), so judge only the *content*: correctness, rigor, novelty, significance,
clarity, and how well claims are supported. Never lower `Presentation`, `Clarity`, or
`Overall` because the paper is long/short or doesn't fit a venue's page count, and never add
a "too long / exceeds page limit" weakness. A longer paper that is thorough and clear should
score *well*, not be marked down for length.

## Outputs
- `projects/<id>/review.json` (validate it parses; all schema fields present).
- Update `state.json`: `stage="review"`, `status="done"` → then set top-level study
  `status="complete"`. Append the verdict to `study.md`.

## Output to the user
Give the headline: Decision, Overall score, the 2–3 biggest strengths and weaknesses,
and any integrity flags. Then summarize the **whole study**: idea → key result → paper →
verdict, with total wall-clock and token cost (from the token log).

---
name: ai-scientist-ideate
description: Stage 1 of the AI Scientist pipeline — generate and refine novel ML research ideas from a topic, with novelty-checking against the literature, and emit them as an AI-Scientist-v2-compatible idea JSON. Use when starting a study or when the user asks for research ideas / hypotheses on a topic.
---

# Stage 1 — Ideation

Generate **novel, feasible** research ideas for a topic and write them out in the exact
AI-Scientist-v2 idea schema so the experiment stage can consume them.

## Inputs
- A **topic** (a sentence) or a workshop-description markdown file under `ideas/`.
  Template: `ideas/TEMPLATE_topic.md`. The example `vendor/AI-Scientist-v2/ai_scientist/ideas/i_cant_believe_its_not_better.md`
  shows the expected style/length of a topic description.
- Optional: `--num <N>` ideas to generate (default 3), `--reflections <R>` refinement
  rounds (default 3).

## Authoritative reference
Mirror upstream prompts and the FinalizeIdea schema:
`vendor/AI-Scientist-v2/ai_scientist/perform_ideation_temp_free.py`
(read `idea_generation_prompt` and the `FinalizeIdea` tool description before writing).

## Idea JSON schema (one object per idea, output a JSON list)
```json
{
  "Name": "lowercase_with_underscores",
  "Title": "Catchy, informative title",
  "Short Hypothesis": "The core hypothesis and why this is the right way to test it.",
  "Related Work": "Most relevant prior work and how this clearly differs (not a trivial extension).",
  "Abstract": "~250-word conference-style abstract.",
  "Experiments": ["Specific, feasible experiment 1 with metrics", "Experiment 2", "..."],
  "Risk Factors and Limitations": ["risk 1", "risk 2"]
}
```

## Procedure
1. **Understand the topic.** If it's a file, read it. If it's a sentence and ambiguous,
   ask 1–2 clarifying questions (domain, datasets allowed, compute budget).
2. **Brainstorm** `N` candidate directions. For each, draft a Short Hypothesis.
3. **Novelty check** each candidate against the literature so you don't reinvent known
   results:
   - Preferred: the upstream Semantic Scholar tool. Quick way to run it through Claude
     Code: `python -m bridge.run vendor/AI-Scientist-v2/ai_scientist/tools/semantic_scholar.py`
     is not a CLI; instead use your **WebSearch** tool to search recent papers, OR call
     the Semantic Scholar API directly with `curl`
     (`https://api.semanticscholar.org/graph/v1/paper/search?query=...`). Set
     `S2_API_KEY` in `.env` if the user has one (higher rate limits); it works without.
   - Drop or sharpen ideas that already exist; note the closest prior work in
     "Related Work".
4. **Reflect** `R` times: for each surviving idea, critique feasibility on *this* machine
   (no GPU — see the umbrella skill's compute reality check), tighten the experiments to
   be small and concrete, and ensure metrics are specified.
5. **Feasibility gate:** every idea's `Experiments` must be runnable on CPU/MPS with
   tiny/synthetic data in minutes-to-an-hour. Rewrite anything that needs a cluster.
6. **Write outputs** into the run dir (create one if none is active):
   - `runs/<id>/idea.json` — the JSON list (validate it parses).
   - `runs/<id>/idea.md` — human-readable version (use
     `aisci.run` helper or mirror upstream `idea_to_markdown`).
   - Update `runs/<id>/state.json`: `stage="ideate"`, `status="done"`, `idea_slug=<Name of chosen idea>`.
   - Append a short note to `runs/<id>/study.md`.

## Output to the user
Present the ideas as a short ranked list (Title + one-line hypothesis + novelty note +
feasibility). Recommend one to take forward, and offer to proceed to
`/ai-scientist-experiment`.

## Bridge fallback
To reproduce upstream ideation exactly (Semantic Scholar loop + reflections, unmodified):
```bash
python -m bridge.run vendor/AI-Scientist-v2/ai_scientist/perform_ideation_temp_free.py \
  --workshop-file ideas/<topic>.md --model gpt-4o-2024-11-20 \
  --max-num-generations 3 --num-reflections 3
```
This writes `ideas/<topic>.json`. Copy it to `runs/<id>/idea.json`. Use this if the user
wants strict upstream parity; otherwise the native procedure above is preferred.

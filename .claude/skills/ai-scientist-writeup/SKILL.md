---
name: ai-scientist-writeup
description: Stage 3 of the AI Scientist pipeline — gather citations and write the experiment results into a conference-style LaTeX paper, compile it to PDF, and reflect/fix until clean. Use after experiments have produced results and plots and the user wants the paper.
---

# Stage 3 — Writeup

Turn `runs/<id>/experiment/` results + plots into a compiled conference-style PDF.

## Authoritative reference
- Templates: `vendor/AI-Scientist-v2/ai_scientist/blank_icml_latex/` (8-page "normal")
  and `vendor/AI-Scientist-v2/ai_scientist/blank_icbinb_latex/` (4-page "icbinb").
- Process to mirror: `vendor/AI-Scientist-v2/ai_scientist/perform_writeup.py`,
  `perform_icbinb_writeup.py` (and `gather_citations`).
- Default to **icbinb (4-page)** for a laptop-scale study unless the user wants the full
  8-page format.

## Prerequisites
- LaTeX toolchain: `pdflatex`/`bibtex` (TeX Live or MacTeX), `chktex` (lint), and
  `poppler` (`pdftoppm`, `pdftotext`) for PDF→image/text. `scripts/doctor.sh` checks
  these. If missing on macOS: `brew install --cask mactex-no-gui` (large) or
  `brew install basictex`, plus `brew install chktex poppler`.

## Procedure
1. **Set up** `runs/<id>/writeup/latex/` by copying the chosen blank template. Keep the
   template's structure (sections, `references.bib`, figure includes).
2. **Gather citations.** Build `references.bib` from real papers:
   - Native: use WebSearch / the Semantic Scholar API (`curl`) to find the ~10–20 most
     relevant papers; write correct BibTeX entries. Verify each exists — **never invent
     citations**.
   - Or bridge-fallback (upstream `gather_citations`, unmodified):
     ```bash
     python -m bridge.run vendor/AI-Scientist-v2/launch_scientist_bfts.py \
       --load_ideas runs/<id>/idea.json --idea_idx 0 --skip_review
     ```
     (this also runs the full writeup; prefer the native path for control).
3. **Write the paper** section by section, grounded **only** in `experiment/` results:
   Title, Abstract, Introduction, Related Work (use the citations), Method, Experiments
   (real numbers, mean±std, from `experiment_results/summary.json`), Results with the
   figures from `experiment/plots/`, Limitations, Conclusion. Report failures honestly —
   negative/partial results are valid (the icbinb venue is literally "I Can't Believe
   It's Not Better").
4. **Insert figures** by copying the plots into the latex dir and `\includegraphics`-ing
   them; use the saved `<fig>.caption.txt` as a starting caption.
5. **Compile** to PDF, iterating on errors:
   ```bash
   .venv/bin/python -m aisci.latex runs/<id>/writeup/latex paper.tex
   ```
   (wraps pdflatex→bibtex→pdflatex×2 and returns the log). Fix LaTeX errors, undefined
   refs/citations, and overfull boxes. Run `chktex` and address warnings.
6. **Reflect** (a few rounds, like upstream `writeup-retries=3`): re-read the compiled
   PDF (open `paper.pdf` with Read — you can see it), check the figures render, captions
   match, claims are supported, page limit is respected. Revise and recompile.
7. **Finalize:** copy the final PDF to `runs/<id>/writeup/paper.pdf`. Update
   `state.json`: `stage="writeup"`, `status="done"`. Note key choices in `study.md`.

## Guardrails
- Every number in the paper must trace to a file in `experiment/`. If a result is
  missing, run it (back to Stage 2) or omit the claim — do not fabricate.
- Every citation must be a real, findable paper.
- Stay within the page limit (4 for icbinb, 8 for normal, excluding references/appendix).

## Output to the user
Report: page count, compile status (clean?), figure list, citation count, and the path
to `paper.pdf`. Offer to proceed to `/ai-scientist-review`.

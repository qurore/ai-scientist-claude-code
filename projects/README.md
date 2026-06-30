# Projects

Each **project** is one self-contained AI-Scientist study. Everything a study
produces lives under its own folder here — nothing project-specific is scattered
elsewhere in the repo:

```
projects/<slug>/
├── state.json            # source of truth (stage, status, idea slug, timestamps)
├── study.md              # lab notebook (chronological log)
├── idea.json, idea.md    # Stage 1 — the chosen idea + alternatives
├── experiment/           # Stage 2 — all implementation & verification lives here
│   ├── code/             #   every script you wrote/ran (lib.py, e1..e4, plots)
│   ├── logs/             #   captured stdout/stderr per run
│   ├── experiment_results/  # metrics JSON + summary.json
│   ├── plots/            #   figures (pdf/png) + .caption.txt
│   ├── journal.jsonl     #   the search trace (one line per node)
│   └── tool_log.jsonl    #   provenance of shell commands (from the hook)
├── writeup/              # Stage 3 — paper
│   ├── latex/            #   paper.tex, references.bib, .sty, compiled paper.pdf
│   ├── figures/          #   figures referenced by the paper
│   └── paper.pdf         #   the finalized PDF
└── review.json           # Stage 4 — the peer review
```

Create one with `/ai-scientist "<topic>"` (or `aisci.run new --slug … --topic …`).

## Projects & privacy (gitignore toggle)

Projects are **gitignored by default** (see the repo `.gitignore`). This lets you
publish the integration layer (`.claude/`, `aisci/`, `bridge/`, `scripts/`, docs)
to a **public** remote without shipping your studies.

- **Public remote, studies stay local:** do nothing — the default. Only this
  `README.md` is tracked under `projects/`.
- **Private repo, version your studies too:** in `.gitignore`, comment out the
  `/projects/*` line (keep the `!` negation lines). Your project folders are then
  tracked. Remember that compiled PDFs, large result files, and any data belong to
  the project and will be committed too.

Either way, a project folder is portable: you can copy a single `projects/<slug>/`
out and `git init` it as its own standalone private repo.

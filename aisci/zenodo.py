"""Deposit a finalized project's paper to Zenodo and (optionally) publish for a DOI.

The only secret is a Zenodo personal access token, read from the environment
(``ZENODO_TOKEN`` for production, ``ZENODO_SANDBOX_TOKEN`` for sandbox) — never
stored in the repo. Author/ORCID/license metadata also come from the environment
(see ``.env.example``). Defaults are deliberately safe:

  * SANDBOX unless ``--production`` (test there first; published DOIs are PERMANENT),
  * DRAFT unless ``--publish`` (so a human can review the deposition in the browser),
  * production publish refuses unless the project's review Decision is ``Accept``
    (override with ``--force``).

    python -m aisci.zenodo deposit projects/<id> [--production] [--publish] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from . import state

PROD_API = "https://zenodo.org/api"
SANDBOX_API = "https://sandbox.zenodo.org/api"
REPO_URL = "https://github.com/qurore/ai-scientist-claude-code"

AI_DISCLOSURE = (
    "This manuscript was generated autonomously by the AI Scientist running inside "
    "Claude Code (Anthropic); every reported number traces to the project's experiment "
    "outputs. It is deposited by the named curator, who takes responsibility for its "
    "release."
)


def _load_dotenv() -> None:
    """Populate os.environ from the repo .env for any missing keys. Robust to values
    that contain spaces/commas/quotes (so `source .env` quirks don't bite). Never
    overrides a value already set in the real environment."""
    p = state.REPO / ".env"
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def _token(production: bool) -> str:
    env = "ZENODO_TOKEN" if production else "ZENODO_SANDBOX_TOKEN"
    tok = os.environ.get(env, "").strip()
    if not tok:
        raise SystemExit(
            f"Missing {env} in the environment. Put it in .env (gitignored) and "
            f"`source .env`, then retry. See .env.example.")
    return tok


def _api(method: str, url: str, token: str, json_body=None, raw=None, content_type=None):
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode()
        headers["Content-Type"] = "application/json"
    elif raw is not None:
        data = raw
        headers["Content-Type"] = content_type or "application/octet-stream"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            body = r.read().decode()
            return r.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            msg = json.loads(body)
        except Exception:
            msg = body
        # never echo the token; surface Zenodo's own error
        raise SystemExit(f"Zenodo API {e.code} on {method} {url.split('?')[0]}: {msg}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Zenodo network error on {method} {url.split('?')[0]}: {e.reason}")


def _chosen_idea(run_id: str) -> dict:
    p = state.project_dir(run_id) / "idea.json"
    if not p.exists():
        return {}
    try:
        ideas = json.loads(p.read_text())
    except Exception:
        return {}
    if not isinstance(ideas, list) or not ideas:
        return {}
    slug = state.load_state(run_id).get("idea_slug")
    for it in ideas:
        if it.get("Name") == slug:
            return it
    return ideas[0]


def _paper_title(run_id: str):
    """The FINAL paper title from writeup/latex/paper.tex (source of truth), cleaned."""
    import re
    p = state.project_dir(run_id) / "writeup" / "latex" / "paper.tex"
    if not p.exists():
        return None
    m = re.search(r"\\title\{(.+?)\}", p.read_text(), re.DOTALL)
    if not m:
        return None
    t = m.group(1)
    t = t.replace("\\bfseries", "").replace("\\\\", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t or None


def _summary(run_id: str) -> dict:
    p = state.project_dir(run_id) / "experiment" / "experiment_results" / "summary.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return {}
    return {}


def build_metadata(run_id: str, publication_type: str = "preprint"):
    st = state.load_state(run_id)
    idea = _chosen_idea(run_id)
    summ = _summary(run_id)
    # Title/abstract from the FINAL artifacts (paper + updated summary), not the
    # original idea (which may predate revisions in the improvement loop).
    title = _paper_title(run_id) or idea.get("Title") or st.get("topic") or run_id
    abstract = "  ".join(x for x in (summ.get("question"), summ.get("overall_conclusion")) if x).strip()
    if not abstract:
        abstract = (idea.get("Abstract") or "").strip()
    desc = abstract + ("<br><br>" if abstract else "") + AI_DISCLOSURE + \
        f'<br><br>Source &amp; method: <a href="{REPO_URL}">{REPO_URL}</a>'

    creators = []
    name = os.environ.get("ZENODO_AUTHOR_NAME", "").strip()
    if name:
        c = {"name": name}
        orcid = os.environ.get("ORCID_ID", "").strip()
        aff = os.environ.get("ZENODO_AUTHOR_AFFILIATION", "").strip()
        if orcid:
            c["orcid"] = orcid
        if aff:
            c["affiliation"] = aff
        creators.append(c)
    # The human curator is the sole author/creator (AI systems cannot take authorship);
    # AI generation is disclosed in the description and notes instead. Fall back to the
    # AI name only if no human is configured.
    if not creators:
        creators.append({"name": "AI Scientist (Claude Code)"})

    stop = {"does", "the", "and", "when", "win", "across", "study", "predict", "right",
            "with", "study", "help", "from", "into", "their", "that", "this", "schedule?"}
    words = [w.strip(",:.?").lower() for w in title.split()]
    kws = [w for w in dict.fromkeys(words) if len(w) > 4 and w not in stop][:5]
    kws += ["learning rate schedules", "edge of stability", "machine learning"]

    meta = {
        "upload_type": "publication",
        "publication_type": publication_type,
        "title": title,
        "creators": creators,
        "description": desc,
        "access_right": "open",
        "license": os.environ.get("ZENODO_DEFAULT_LICENSE", "cc-by-4.0"),
        "keywords": kws,
        "related_identifiers": [
            {"relation": "isDerivedFrom", "identifier": REPO_URL, "scheme": "url"},
        ],
        "notes": AI_DISCLOSURE,
    }
    return meta, title


def deposit(run_id: str, production=False, publish=False, publication_type="preprint",
            force=False, dry_run=False) -> dict:
    _load_dotenv()
    pdir = state.project_dir(run_id)
    pdf = pdir / "writeup" / "paper.pdf"
    if not pdf.exists():
        raise SystemExit(f"No paper at {pdf}. Run the writeup stage first.")
    st = state.load_state(run_id)
    if st.get("status") != "complete":
        print(f"[warn] project status is {st.get('status')!r}, not 'complete'.", file=sys.stderr)

    meta, title = build_metadata(run_id, publication_type)

    if dry_run:
        print(json.dumps({"dry_run": True,
                          "environment": "production" if production else "sandbox",
                          "would_publish": publish, "pdf": str(pdf), "metadata": meta}, indent=2))
        return {"dry_run": True}

    if publish and production and not force:
        review = {}
        rp = pdir / "review.json"
        if rp.exists():
            try:
                review = json.loads(rp.read_text())
            except Exception:
                review = {}
        if review.get("Decision") != "Accept":
            raise SystemExit(
                "Refusing to PUBLISH to production: review Decision is not 'Accept' "
                f"(got {review.get('Decision')!r}). Re-run with --force to override.")

    base = PROD_API if production else SANDBOX_API
    token = _token(production)

    # 1) create draft deposition
    _, dep = _api("POST", f"{base}/deposit/depositions", token, json_body={})
    dep_id = dep["id"]
    bucket = dep["links"]["bucket"]
    # 2) upload the PDF (Zenodo bucket API requires application/octet-stream)
    _api("PUT", f"{bucket}/paper.pdf", token, raw=pdf.read_bytes(),
         content_type="application/octet-stream")
    # 3) attach metadata
    _, dep2 = _api("PUT", f"{base}/deposit/depositions/{dep_id}", token, json_body={"metadata": meta})

    rec = {
        "environment": "production" if production else "sandbox",
        "deposition_id": dep_id,
        "draft_url": dep["links"].get("html"),
        "title": title,
        "published": False,
        "reserved_doi": (dep2.get("metadata", {}).get("prereserve_doi", {}) or {}).get("doi"),
    }
    if publish:
        _, pub = _api("POST", f"{base}/deposit/depositions/{dep_id}/actions/publish", token)
        rec["published"] = True
        rec["doi"] = pub.get("doi")
        rec["record_url"] = (pub.get("links", {}) or {}).get("record_html")
    (pdir / "zenodo.json").write_text(json.dumps(rec, indent=2))
    print(json.dumps(rec, indent=2))
    return rec


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="aisci.zenodo")
    sub = p.add_subparsers(dest="cmd", required=True)
    pd = sub.add_parser("deposit", help="deposit a project's paper.pdf to Zenodo")
    pd.add_argument("project", help="project id or projects/<id>")
    pd.add_argument("--production", action="store_true", help="use zenodo.org (default: sandbox)")
    pd.add_argument("--publish", action="store_true", help="publish (PERMANENT); default: draft only")
    pd.add_argument("--publication-type", default="preprint")
    pd.add_argument("--force", action="store_true", help="allow production publish without an Accept review")
    pd.add_argument("--dry-run", action="store_true", help="print the metadata; no token/network")
    args = p.parse_args(argv)
    run_id = Path(args.project).name
    deposit(run_id, production=args.production, publish=args.publish,
            publication_type=args.publication_type, force=args.force, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

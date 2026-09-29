"""Collect ALCE `*.score` files into one markdown table.

  python summarize_scores.py --runs-dir runs/m2 --extra $ALCE_DIR/result --out results/m2_scores.md

Rows are keyed by dataset and file name; citation F1 is the harmonic mean of
ALCE's citation_rec / citation_prec (the paper reports all three).
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ORDER = ["dense_gtr_xxl", "keyword_jaccard", "full_token_jaccard", "citefix_intersection",
         "citefix_ksc", "tfidf", "bm25", "splade"]
LABEL = {
    "dense_gtr_xxl": "Dense MIPS (gtr-t5-xxl) — baseline",
    "keyword_jaccard": "Keyword Jaccard — proposed",
    "full_token_jaccard": "E1 full-token Jaccard",
    "citefix_intersection": "E2 CiteFix §3.1",
    "citefix_ksc": "E3 CiteFix §3.2 KSC",
    "tfidf": "E7 TF-IDF",
    "bm25": "E8 BM25",
    "splade": "E9 SPLADE",
}


def f1(p: float, r: float) -> float:
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


def row_for(score_path: Path) -> dict:
    s = json.load(open(score_path))
    name = score_path.name[: -len(".score")]
    m = re.match(r"(asqa|qampari)-(gen|gold)-(.+)-top(\d+)-t([\d.]+)-th([\d.]+)\.json$", name)
    if m:
        ds, _, method, _, _, th = m.groups()
        label = LABEL.get(method, method) + (f" (threshold {th})" if float(th) > 0 else "")
        rank = ORDER.index(method) if method in ORDER else len(ORDER)
    else:  # generator's own citations or ALCE's post_hoc_cite output
        ds = "asqa" if name.startswith("asqa") else "qampari"
        label = ("ALCE post_hoc_cite gtr-t5-xxl (reference)" if "post_hoc_cite" in name
                 else "Generator's own in-context citations (reference)")
        rank, th = 100, "-"
    rec, prec = s.get("citation_rec", float("nan")), s.get("citation_prec", float("nan"))
    return {"ds": ds, "rank": rank, "th": th, "label": label, "rec": rec, "prec": prec,
            "f1": f1(prec, rec), "file": name}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", required=True)
    ap.add_argument("--extra", nargs="*", default=[], help="more *.score files or dirs (references)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    paths = sorted(Path(a.runs_dir).glob("*.score"))
    for e in a.extra:
        p = Path(e)
        paths += sorted(p.glob("*.score")) if p.is_dir() else [p]
    rows = sorted((row_for(p) for p in paths), key=lambda r: (r["ds"], r["rank"], str(r["th"])))

    lines = []
    for ds in ["asqa", "qampari"]:
        sub = [r for r in rows if r["ds"] == ds]
        if not sub:
            continue
        lines += [f"### {ds.upper()}", "", "| Method | Citation Recall | Citation Precision | F1 |",
                  "| --- | ---: | ---: | ---: |"]
        lines += [f"| {r['label']} | {r['rec']:.1f} | {r['prec']:.1f} | {r['f1']:.1f} |" for r in sub]
        lines.append("")
    text = "\n".join(lines)
    print(text)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n")


if __name__ == "__main__":
    main()

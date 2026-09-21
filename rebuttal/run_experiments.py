"""Orchestrator: build citation files for every method, then score them with ALCE.

Scoring calls ALCE's own eval.py, so the numbers are produced by the same
protocol the paper already used.  That step loads google/t5_xxl_true_nli_mixture
(T5-XXL, 11B) and is the only part needing a large GPU -- see SERVER.md.

  # CPU: build citation files for the lexical baselines
  python run_experiments.py --build --methods full_token_jaccard,citefix_intersection,tfidf,bm25

  # GPU: cache keywords, then build the proposed method too
  python extract_keywords.py --dataset asqa --extractor general
  python run_experiments.py --build --methods keyword_jaccard \
      --keyword-cache cache/asqa-general-stem-top5.pkl

  # GPU: score everything
  python run_experiments.py --eval
"""

from __future__ import annotations

import argparse
import pickle
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import alce_adapter as A  # noqa: E402

HERE = Path(__file__).parent
RUNS = HERE / "runs"
ALL_METHODS = ["keyword_jaccard", "full_token_jaccard", "citefix_intersection",
               "citefix_ksc", "tfidf", "bm25"]


def do_build(args):
    cache = pickle.load(open(args.keyword_cache, "rb")) if args.keyword_cache else None
    for dataset in args.datasets.split(","):
        for method in args.methods.split(","):
            payload, dropped = A.build(
                dataset, method, top_k=args.top_k, temperature=args.temperature,
                threshold=args.threshold, limit=args.limit, text_field=args.field,
                keyword_cache=cache)
            name = f"{dataset}-{method}-top{args.top_k}-t{args.temperature}-th{args.threshold}"
            path = A.write(payload, RUNS, name)
            print(f"  {dataset:8s} {method:22s} items={len(payload['data']):4d} "
                  f"dropped={dropped:3d} -> {path.name}")


def do_eval(args):
    """Run ALCE eval.py on every built file. Needs the large GPU."""
    alce = Path(args.alce).expanduser()
    files = sorted(RUNS.glob("*.json"))
    if not files:
        sys.exit("no files in runs/ -- run --build first")
    for f in files:
        if f.with_suffix(".json.score").exists() and not args.overwrite:
            print(f"  skip (scored): {f.name}")
            continue
        flags = ["--citations"] + (["--qa", "--mauve"] if "asqa" in f.name else [])
        cmd = [sys.executable, "eval.py", "--f", str(f.resolve()), *flags]
        print(f"  $ {' '.join(cmd)}")
        if not args.dry_run:
            subprocess.run(cmd, cwd=alce, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--eval", action="store_true")
    ap.add_argument("--datasets", default="asqa,qampari")
    ap.add_argument("--methods", default=",".join(m for m in ALL_METHODS if m != "keyword_jaccard"))
    ap.add_argument("--field", default="answer", help="answer (gold) or output (generated)")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=0.05)
    ap.add_argument("--threshold", type=float, default=0.0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--keyword-cache", default=None)
    ap.add_argument("--alce", default="~/Desktop/gsds/Research/ALCE")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not (a.build or a.eval):
        ap.error("pass --build and/or --eval")
    if a.build:
        do_build(a)
    if a.eval:
        do_eval(a)


if __name__ == "__main__":
    main()

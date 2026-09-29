"""Orchestrator: build citation files for every method, then score them with ALCE.

Scoring calls ALCE's own eval.py, so the numbers are produced by the same
protocol the paper already used.  That step loads google/t5_xxl_true_nli_mixture
(T5-XXL, 11B) and is the only part needing a large GPU -- see SERVER.md.

Inputs are LLM-generated answers from ALCE's run.py (`--result DATASET=PATH`);
without --result the gold `answer` of the raw eval file is cited instead.

  # CPU: build citation files for the lexical baselines
  python run_experiments.py --build --datasets asqa \
      --result asqa=$ALCE_DIR/result/asqa-....json \
      --methods full_token_jaccard,citefix_intersection,citefix_ksc,tfidf,bm25

  # GPU: cache keywords from the same file, then build the proposed method too
  python extract_keywords.py --dataset asqa --extractor general --result $ALCE_DIR/result/asqa-....json
  python run_experiments.py --build --datasets asqa --result asqa=$ALCE_DIR/result/asqa-....json \
      --methods keyword_jaccard --keyword-cache cache/asqa-gen-general-stem-top5.pkl

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
ALL_METHODS = ["dense_gtr_xxl", "keyword_jaccard", "full_token_jaccard",
               "citefix_intersection", "citefix_ksc", "tfidf", "bm25"]


def parse_results(specs):
    """--result asqa=path --result qampari=path  ->  {dataset: path}"""
    out = {}
    for spec in specs or []:
        dataset, _, path = spec.partition("=")
        if not path:
            sys.exit(f"--result expects DATASET=PATH, got {spec!r}")
        out[dataset] = path
    return out


def do_build(args):
    cache = pickle.load(open(args.keyword_cache, "rb")) if args.keyword_cache else None
    results = parse_results(args.result)
    for dataset in args.datasets.split(","):
        result = results.get(dataset)
        field = args.field or ("output" if result else "answer")
        src = "gen" if result else "gold"
        for method in args.methods.split(","):
            payload, dropped = A.build(
                dataset, method, top_k=args.top_k, temperature=args.temperature,
                threshold=args.threshold, limit=args.limit, text_field=field,
                keyword_cache=cache, result=result)
            name = f"{dataset}-{src}-{method}-top{args.top_k}-t{args.temperature}-th{args.threshold}"
            path = A.write(payload, Path(args.runs_dir), name)
            print(f"  {dataset:8s} {method:22s} items={len(payload['data']):4d} "
                  f"dropped={dropped:3d} -> {path.name}")


def do_eval(args):
    """Run ALCE eval.py on every built file. Needs the large GPU."""
    alce = Path(args.alce).expanduser()
    files = sorted(Path(args.runs_dir).glob("*.json"))
    if not files:
        sys.exit(f"no files in {args.runs_dir} -- run --build first")
    for f in files:
        if f.with_suffix(".json.score").exists() and not args.overwrite:
            print(f"  skip (scored): {f.name}")
            continue
        # Re-cited files share the generated text, so answer-quality metrics
        # (--qa/--mauve) are identical across methods; score citations only.
        flags = args.eval_flags.split()
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
    ap.add_argument("--field", default=None,
                    help="answer (gold) or output (generated); default: output with --result, else answer")
    ap.add_argument("--result", action="append", metavar="DATASET=PATH",
                    help="ALCE run.py output JSON with generated answers, e.g. asqa=result/asqa-....json")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=0.05)
    ap.add_argument("--threshold", type=float, default=0.0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--keyword-cache", default=None)
    ap.add_argument("--alce", default=str(A.ALCE_DIR), help="ALCE checkout (default: $ALCE_DIR or ~/ALCE)")
    ap.add_argument("--runs-dir", default=str(RUNS), help="where built citation files go / are scored from")
    ap.add_argument("--eval-flags", default="--citations", help="flags passed to ALCE eval.py")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    A.set_alce_dir(a.alce)

    if not (a.build or a.eval):
        ap.error("pass --build and/or --eval")
    if a.build:
        do_build(a)
    if a.eval:
        do_eval(a)


if __name__ == "__main__":
    main()

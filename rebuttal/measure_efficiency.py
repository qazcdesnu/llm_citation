"""E10 / E11 -- the fair efficiency re-measurement for Point 4.

What the paper currently reports:
  Fig. 6 (Appendix C.1) times the proposed method from PRECOMPUTED keyword
  columns while timing TF-IDF and LCS from raw text, so the BERT/BioBERT
  inference cost is absent from the 0.045s figure.
  Fig. 3's measurement script is not in the repository at all.

What this script reports instead: for every method, wall-clock from raw text to
score matrix, with feature extraction inside the timed region, plus model load
time and peak GPU memory.  The proposed method is timed twice -- with and
without extraction -- so the paper can state both honestly.

NOTE: untested -- written on a machine that cannot load the models.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import alce_adapter as A  # noqa: E402
from baselines import SCORERS, Context  # noqa: E402


def gpu_peak_mb() -> float:
    try:
        import torch
        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / 1024 ** 2
    except Exception:
        pass
    return float("nan")


def reset_gpu():
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats()
    except Exception:
        pass


def timed_load(fn):
    reset_gpu()
    t0 = time.perf_counter()
    obj = fn()
    return obj, time.perf_counter() - t0, gpu_peak_mb()


def dense_baseline(model_name="sentence-transformers/gtr-t5-large", device="cuda"):
    """The comparison point used in the paper (ALCE dense MIPS)."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(model_name, device=device)

    def score(sentences, documents, ctx):
        s = model.encode(sentences, convert_to_numpy=True, show_progress_bar=False)
        d = model.encode(documents, convert_to_numpy=True, show_progress_bar=False)
        return s @ d.T
    return score


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="asqa", choices=["asqa", "qampari"])
    ap.add_argument("--field", default="answer")
    ap.add_argument("--limit", type=int, default=200, help="paper used 200 responses")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--extractor", default="general", choices=["domain", "general"])
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--out", default="results/efficiency.json")
    a = ap.parse_args()

    items = A.load(a.dataset, limit=a.limit)
    payloads = []
    for it in items:
        sents = A.split(it[a.field], a.dataset, it["question"])
        docs = [f"{d['title']} {d['text']}" for d in it["docs"][:a.top_k]]
        if sents and docs:
            scores = np.array([float(d.get("score", 0.0)) for d in it["docs"][:a.top_k]])
            payloads.append((sents, docs, scores))
    n_sent = sum(len(s) for s, _, _ in payloads)
    report = {"dataset": a.dataset, "responses": len(payloads), "sentences": n_sent, "methods": {}}

    def record(name, load_s, load_mb, run_s, run_mb, note=""):
        report["methods"][name] = {
            "load_seconds": round(load_s, 4), "load_peak_mb": round(load_mb, 1),
            "inference_seconds": round(run_s, 4), "inference_peak_mb": round(run_mb, 1),
            "ms_per_sentence": round(run_s / max(n_sent, 1) * 1000, 4), "note": note,
        }
        print(f"  {name:32s} load {load_s:7.2f}s / infer {run_s:7.3f}s "
              f"({run_s/max(n_sent,1)*1000:6.3f} ms/sent)  peak {run_mb:8.1f} MB  {note}")

    print(f"{a.dataset}: {len(payloads)} responses, {n_sent} sentences\n")

    # --- lexical methods: no model to load, extraction is inside the timing
    for name in ["full_token_jaccard", "citefix_intersection", "citefix_ksc", "tfidf", "bm25"]:
        reset_gpu()
        t0 = time.perf_counter()
        for sents, docs, sc in payloads:
            SCORERS[name](sents, docs, Context(retrieval_scores=sc))
        record(name, 0.0, 0.0, time.perf_counter() - t0, gpu_peak_mb(), "CPU, extraction included")

    # --- proposed method, timed honestly and the way Fig. 6 timed it
    import extract_keywords as EK
    pipes, load_s, load_mb = timed_load(lambda: EK.build_pipelines(a.extractor, device=a.device))

    reset_gpu()
    t0 = time.perf_counter()
    cached = []
    for sents, docs, _ in payloads:
        ks = EK.extract(sents, pipes)
        kd = EK.extract(docs, pipes)
        cached.append((ks, kd))
        SCORERS["keyword_jaccard"](sents, docs, Context(keyword_sentences=ks, keyword_documents=kd))
    record("keyword_jaccard (E10 fair)", load_s, load_mb, time.perf_counter() - t0,
           gpu_peak_mb(), "extraction INCLUDED -- this is the honest number")

    reset_gpu()
    t0 = time.perf_counter()
    for (sents, docs, _), (ks, kd) in zip(payloads, cached):
        SCORERS["keyword_jaccard"](sents, docs, Context(keyword_sentences=ks, keyword_documents=kd))
    record("keyword_jaccard (as Fig. 6)", 0.0, 0.0, time.perf_counter() - t0,
           gpu_peak_mb(), "extraction EXCLUDED -- reproduces the current figure")

    # --- dense baseline (E11 comparison point)
    try:
        scorer, load_s, load_mb = timed_load(dense_baseline)
        reset_gpu()
        t0 = time.perf_counter()
        for sents, docs, _ in payloads:
            scorer(sents, docs, None)
        record("dense_gtr_t5_large", load_s, load_mb, time.perf_counter() - t0, gpu_peak_mb())
    except Exception as e:  # noqa: BLE001
        print(f"  dense baseline skipped: {type(e).__name__}: {e}")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()

"""E10 -- the fair efficiency re-measurement for Point 4 (Fig. 6 / Appendix C.1).

What the paper reports: Fig. 6 times the proposed method on 200 generated
PubMedQA responses (appendix_data.pkl) from PRECOMPUTED keyword columns
(`keyword_sentences` / `keyword_documents`), while TF-IDF and LCS build their
features from raw text inside the timed loop. The BERT/BioBERT extraction cost is
therefore absent from the reported 0.045 s.

What this script reports, on the same 200 responses: for every citation method,
wall-clock from raw text to the (sentences x documents) score matrix, with feature
extraction inside the timed region; model load time; and peak GPU memory.
The proposed method is timed three ways:
  - "as Fig. 6":      Jaccard over the keyword columns already in the pickle
  - "+ extraction":   keywords extracted from raw text inside the timing (fair)
  - both extractors:  domain (3 BioBERT NER) and general (1 BERT keyword model)

Every timing is the median of --repeats runs after one warm-up pass; GPU work is
synchronised before the clock stops.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import statistics
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import baselines as B  # noqa: E402
from baselines import SCORERS, Context  # noqa: E402

PKL = Path(__file__).parent.parent / "code" / "code" / "appendix_data.pkl"
SPLIT = re.compile(r'[^0-9]["."][^0-9]')  # citation.py's sentence splitter (as in run_smoke.py)


def split_sentences(text):
    return [x.strip() for x in SPLIT.split(text) if x.strip()] or [""]


def sync():
    import torch
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def reset_peak():
    import torch
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()


def peak_mb() -> float:
    import torch
    return torch.cuda.max_memory_allocated() / 1024 ** 2 if torch.cuda.is_available() else 0.0


def timed(fn, repeats: int):
    """Warm up once, then median wall-clock over `repeats` runs; peak GPU MB of those runs."""
    fn()
    sync()
    reset_peak()
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        sync()
        times.append(time.perf_counter() - t0)
    return statistics.median(times), peak_mb(), times


def free_gpu():
    import gc
    import torch
    B._GTR_MODELS.clear()
    B._SPLADE.clear()
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def timed_load(fn, unload):
    """Load twice and report the second (warm) load.

    The first read of a checkpoint comes off NFS and mostly measures the file
    server; the warm load is the model-initialisation cost the method itself has.
    """
    fn()
    unload()
    free_gpu()
    reset_peak()
    t0 = time.perf_counter()
    obj = fn()
    sync()
    return obj, time.perf_counter() - t0, peak_mb()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=32, help="NER batch, matches encode() default")
    ap.add_argument("--out", default="results/e10_efficiency.json")
    a = ap.parse_args()

    import torch
    df = pd.read_pickle(PKL)
    rows = []
    for _, r in df.iterrows():
        docs = [d.page_content for d in r["sources"]]
        if docs:
            # the pickle wraps each list of keyword sets once more: [[{...}, {...}]]
            rows.append({"sents": split_sentences(r["generated_answer"]), "docs": docs,
                         "ks": r["keyword_sentences"][0], "kd": r["keyword_documents"][0]})
    n_sent = sum(len(x["sents"]) for x in rows)
    n_pairs = sum(len(x["sents"]) * len(x["docs"]) for x in rows)
    env = {"gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
           "cpu": platform.processor() or platform.machine(), "torch": torch.__version__,
           "repeats": a.repeats}
    report = {"data": str(PKL.name), "responses": len(rows), "sentences": n_sent,
              "pairs": n_pairs, "env": env, "methods": {}}
    print(f"{len(rows)} responses, {n_sent} sentences, {n_pairs} sentence-document pairs | {env}\n")

    batch = a.batch_size

    def record(name, run_s, run_mb, load_s=0.0, load_mb=0.0, device="cpu", note="", runs=None):
        report["methods"][name] = {
            "device": device, "load_seconds": round(load_s, 3), "load_peak_gpu_mb": round(load_mb, 1),
            "inference_seconds": round(run_s, 4), "inference_peak_gpu_mb": round(run_mb, 1),
            "ms_per_sentence": round(run_s / n_sent * 1000, 4), "runs": [round(t, 4) for t in runs or []],
            "note": note,
        }
        print(f"  {name:40s} {device:4s} load {load_s:7.2f}s ({load_mb:8.1f} MB) | infer {run_s:8.3f}s "
              f"({run_s / n_sent * 1000:7.3f} ms/sent, peak {run_mb:8.1f} MB)  {note}")

    # 1) proposed, exactly as Fig. 6 measured it (keywords read from the pickle)
    def kw_precomputed():
        for x in rows:
            SCORERS["keyword_jaccard"](x["sents"], x["docs"],
                                       Context(keyword_sentences=x["ks"], keyword_documents=x["kd"]))
    t, mb, runs = timed(kw_precomputed, a.repeats)
    record("keyword_jaccard (as Fig. 6: keywords precomputed)", t, mb, runs=runs,
           note="extraction EXCLUDED -- reproduces the current figure")

    # 2) proposed with extraction inside the timing, for both extractors
    import extract_keywords as EK
    for kind in ["domain", "general"]:
        holder = {}

        def load(kind=kind):
            holder["p"] = EK.build_pipelines(kind, device=a.device)
            return holder["p"]
        pipes, load_s, load_mb = timed_load(load, holder.clear)

        def kw_with_extraction():
            for x in rows:
                ks = EK.extract(x["sents"], pipes, batch_size=batch)
                kd = EK.extract(x["docs"], pipes, batch_size=batch)
                SCORERS["keyword_jaccard"](x["sents"], x["docs"],
                                           Context(keyword_sentences=ks, keyword_documents=kd))
        t, mb, runs = timed(kw_with_extraction, a.repeats)
        record(f"keyword_jaccard + extraction ({kind})", t, mb, load_s, load_mb, "gpu", runs=runs,
               note=f"{len(pipes)} NER model(s), batch {batch}, extraction INCLUDED")
        del pipes
        holder.clear()
        free_gpu()

    # 3) lexical baselines: no model, tokenisation inside the timing
    for name in ["full_token_jaccard", "citefix_intersection", "citefix_ksc", "tfidf", "bm25"]:
        def run(name=name):
            for x in rows:
                SCORERS[name](x["sents"], x["docs"], Context())
        t, mb, runs = timed(run, a.repeats)
        record(name, t, 0.0, runs=runs)

    # 4) neural baselines: dense (the paper's comparison point, Fig. 3) and SPLADE
    for label, load, scorer_name, kwargs in [
        ("dense gtr-t5-xxl", lambda: B.load_gtr("gtr-t5-xxl"), "dense_gtr_xxl", {"name": "gtr-t5-xxl"}),
        ("dense gtr-t5-large", lambda: B.load_gtr("gtr-t5-large"), "dense_gtr_xxl", {"name": "gtr-t5-large"}),
        ("splade (SPLADE++)", lambda: B.load_splade(), "splade", {}),
    ]:

        def run(scorer_name=scorer_name, kwargs=kwargs):
            for x in rows:
                SCORERS[scorer_name](x["sents"], x["docs"], Context(), **kwargs)
        model, load_s, load_mb = timed_load(load, free_gpu)
        t, mb, runs = timed(run, a.repeats)
        record(label, t, mb, load_s, load_mb, "gpu", runs=runs, note="fp32, batch 32")
        del model   # drop the last reference so the next model's peak is its own
        free_gpu()

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    json.dump(report, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()

"""M1 smoke test: run every scorer through the shared path on appendix_data.pkl.

This file has no gold citation labels, so nothing here is an accuracy number.
It checks that (a) every scorer runs and returns a well-formed matrix, (b) the
shared calibration path works, and (c) it measures how far the methods actually
diverge in their citation assignments -- which is what Point 2 turns on.
"""

import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from baselines import SCORERS, Context, assign, softmax  # noqa: E402

PKL = Path(__file__).parent.parent / "code" / "code" / "appendix_data.pkl"
SPLIT = re.compile(r'[^0-9]["."][^0-9]')  # citation.py's sentence splitter


def split_sentences(text):
    return [x.strip() for x in SPLIT.split(text) if x.strip()] or [""]


def main():
    df = pd.read_pickle(PKL)
    names = list(SCORERS)
    timings = {n: 0.0 for n in names}
    assigns = {n: [] for n in names}
    n_sent = 0
    skipped = 0

    for _, row in df.iterrows():
        sentences = split_sentences(row["generated_answer"])
        documents = [d.page_content for d in row["sources"]]
        if not documents:
            skipped += 1
            continue

        ks = row["keyword_sentences"][0]
        kd = row["keyword_documents"][0]
        # The extractor emits one keyword set per sentence; the splitter can
        # disagree on sentence count, so align to the shorter of the two.
        if len(ks) != len(sentences):
            sentences = sentences[: len(ks)]
            ks = ks[: len(sentences)]
        if len(kd) != len(documents):
            m = min(len(kd), len(documents))
            documents, kd = documents[:m], kd[:m]
        if not sentences or not documents:
            skipped += 1
            continue

        ctx = Context(query=row["question"], keyword_sentences=ks, keyword_documents=kd)
        n_sent += len(sentences)

        for name in names:
            t0 = time.perf_counter()
            raw = SCORERS[name](sentences, documents, ctx)
            timings[name] += time.perf_counter() - t0
            assert raw.shape == (len(sentences), len(documents)), (name, raw.shape)
            assigns[name].append(assign(softmax(raw, 0.05), 0.0))

    for n in names:
        assigns[n] = np.concatenate(assigns[n])

    print(f"rows={len(df)}  skipped={skipped}  sentences={n_sent}\n")

    print("Scoring time over the whole file (extraction cost NOT included for")
    print("keyword_jaccard -- it reads precomputed keywords, exactly as")
    print("processing_time.ipynb does; see E10):")
    for n in names:
        print(f"  {n:22s} {timings[n]:7.3f} s   ({timings[n]/n_sent*1000:6.3f} ms/sentence)")

    print("\nAssignment agreement (fraction of sentences citing the same document):")
    print(f"  {'':22s}" + "".join(f"{n[:10]:>12s}" for n in names))
    for a in names:
        cells = "".join(f"{float((assigns[a] == assigns[b]).mean()):12.3f}" for b in names)
        print(f"  {a:22s}{cells}")

    kj, ft = assigns["keyword_jaccard"], assigns["full_token_jaccard"]
    print(f"\nPoint 2 axis -- keyword_jaccard vs full_token_jaccard:")
    print(f"  identical assignment on {float((kj == ft).mean())*100:.1f}% of sentences")


if __name__ == "__main__":
    main()

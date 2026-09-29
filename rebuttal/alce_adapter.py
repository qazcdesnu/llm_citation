"""Bridge between our scorers and the ALCE evaluation harness.

ALCE's eval.py expects {"args": ..., "data": [item, ...]} where each item has
`output` carrying 1-based [n] citation markers into `item['docs']`.  We build
that file so `python eval.py --f <file> --citations` scores our assignments with
exactly the protocol the paper already used -- no home-grown metric.

Sentence segmentation mirrors eval.py so our markers land on the same units the
evaluator will score (nltk sent_tokenize; comma-split for QAMPARI).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import numpy as np
from nltk import sent_tokenize

sys.path.insert(0, str(Path(__file__).parent))
from baselines import SCORERS, Context, assign, softmax  # noqa: E402

# Set ALCE_DIR to the ALCE checkout (e.g. /shared/s3/lab03/jinwoongkim/ALCE on GSDS).
ALCE_DIR = Path(os.environ.get("ALCE_DIR", "~/ALCE")).expanduser()
DATA = ALCE_DIR / "data"


def set_alce_dir(path) -> None:
    global ALCE_DIR, DATA
    ALCE_DIR = Path(path).expanduser()
    DATA = ALCE_DIR / "data"


def remove_citations(sent: str) -> str:
    """Copied from ALCE utils.py so stripped text matches what eval.py scores."""
    return re.sub(r"\[\d+", "", re.sub(r" \[\d+", "", sent)).replace(" |", "").replace("]", "")


def load(dataset: str, retriever: str = "gtr", limit: int | None = None,
         result: str | Path | None = None) -> list[dict]:
    """ALCE eval items.

    Without `result`: the raw eval file (gold `answer`, top-100 docs, no generation).
    With `result`: a run.py output (`result/*.json`) -- the sample run.py drew
    (`--quick_test`, `--seed`), its generated `output`, and the `ndoc` docs that
    were in the prompt. Citation markers the generator wrote are stripped, so every
    method re-cites the same text; the original is kept as `output_raw`.
    """
    if result is not None:
        path = Path(result).expanduser()
        if not path.exists():
            sys.exit(f"ALCE result file not found: {path}")
        items = json.load(open(path))["data"]
        for it in items:
            out = it["output"][0] if isinstance(it["output"], list) else it["output"]
            it["output_raw"] = out
            it["output"] = remove_citations(out).strip()
        return items[:limit] if limit else items

    path = DATA / f"{dataset}_eval_{retriever}_top100.json"
    if not path.exists():
        sys.exit(f"ALCE data not found: {path}\n"
                 "set ALCE_DIR (or --alce) to the ALCE checkout and run download_data.sh")
    items = json.load(open(path))
    return items[:limit] if limit else items


def split(text: str, dataset: str, question: str) -> list[str]:
    """Mirror eval.py's segmentation so markers align with scored units."""
    if dataset == "qampari":
        return [x.strip() for x in text.rstrip().rstrip(".").rstrip(",").split(",") if x.strip()]
    return sent_tokenize(text)


def cite_item(item, dataset, scorer, top_k, temperature, threshold,
              text_field="answer", keywords=None):
    """Assign one citation per sentence over the top-k retrieved docs.

    `keywords` is one entry from the cache written by extract_keywords.py; it is
    required for the proposed method and ignored by every lexical baseline.
    """
    docs = item["docs"][:top_k]
    sentences = split(item[text_field], dataset, item["question"])
    if not sentences or not docs:
        return None

    contents = [f"{d['title']} {d['text']}" for d in docs]
    ctx = Context(
        query=item["question"],
        retrieval_scores=np.array([float(d.get("score", 0.0)) for d in docs]),
    )
    if scorer == "keyword_jaccard":
        if keywords is None:
            raise ValueError(
                "keyword_jaccard needs a keyword cache -- run extract_keywords.py first")
        ks, kd = keywords["keyword_sentences"], keywords["keyword_documents"]
        # The extractor and the splitter can disagree on counts; align down.
        n_s, n_d = min(len(ks), len(sentences)), min(len(kd), len(contents))
        if n_s == 0 or n_d == 0:
            return None
        sentences, contents = sentences[:n_s], contents[:n_d]
        docs = docs[:n_d]
        ctx.keyword_sentences, ctx.keyword_documents = ks[:n_s], kd[:n_d]

    raw = SCORERS[scorer](sentences, contents, ctx)
    picks = assign(softmax(raw, temperature), threshold)

    cited = [s if p < 0 else f"{s} [{int(p) + 1}]" for s, p in zip(sentences, picks)]
    # QAMPARI units are comma-separated answers; eval.py re-splits on ",", so the
    # commas must survive ("A [1], B [2]."). ASQA sentences are space-joined.
    out = ", ".join(cited) + "." if dataset == "qampari" else " ".join(cited)
    new = dict(item)
    new["docs"] = docs
    new["output"] = out
    return new


def build(dataset, scorer, top_k=5, temperature=0.05, threshold=0.0,
          limit=None, retriever="gtr", text_field="answer", keyword_cache=None,
          result=None):
    items = load(dataset, retriever, limit, result)
    if keyword_cache is not None:
        check_cache_alignment(items, keyword_cache)
    data, dropped = [], 0
    for idx, it in enumerate(items):
        kw = keyword_cache[idx] if keyword_cache is not None and idx < len(keyword_cache) else None
        new = cite_item(it, dataset, scorer, top_k, temperature, threshold, text_field, kw)
        if new is None:
            dropped += 1
            continue
        data.append(new)
    config = {
        "scorer": scorer, "dataset": dataset, "top_k": top_k,
        "temperature": temperature, "threshold": threshold,
        "text_field": text_field, "retriever": retriever,
        "keyword_cache": bool(keyword_cache),
        "result": str(result) if result else None,
        "note": "citations assigned post-hoc by rebuttal/alce_adapter.py",
    }
    return {"args": config, "data": data}, dropped


def check_cache_alignment(items, cache) -> None:
    """The keyword cache is matched to items by position; fail loudly if it drifts."""
    if len(cache) != len(items):
        sys.exit(f"keyword cache has {len(cache)} entries but input has {len(items)} items "
                 "-- was it built from the same file (--result) and --limit?")
    for i, (it, entry) in enumerate(zip(items, cache)):
        q = entry.get("question")
        if q is not None and q != it["question"]:
            sys.exit(f"keyword cache misaligned at item {i}: {q[:60]!r} != {it['question'][:60]!r}")


def write(payload, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    json.dump(payload, open(path, "w"), indent=2)
    return path

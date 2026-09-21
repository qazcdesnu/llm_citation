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
import sys
from pathlib import Path

import numpy as np
from nltk import sent_tokenize

sys.path.insert(0, str(Path(__file__).parent))
from baselines import SCORERS, Context, assign, softmax  # noqa: E402

ALCE_DIR = Path.home() / "Desktop" / "gsds" / "Research" / "ALCE"
DATA = ALCE_DIR / "data"


def load(dataset: str, retriever: str = "gtr", limit: int | None = None) -> list[dict]:
    path = DATA / f"{dataset}_eval_{retriever}_top100.json"
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

    out = " ".join(
        s if p < 0 else f"{s} [{int(p) + 1}]" for s, p in zip(sentences, picks)
    )
    new = dict(item)
    new["docs"] = docs
    new["output"] = out
    return new


def build(dataset, scorer, top_k=5, temperature=0.05, threshold=0.0,
          limit=None, retriever="gtr", text_field="answer", keyword_cache=None):
    items = load(dataset, retriever, limit)
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
        "note": "citations assigned post-hoc by rebuttal/alce_adapter.py",
    }
    return {"args": config, "data": data}, dropped


def write(payload, out_dir: Path, name: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.json"
    json.dump(payload, open(path, "w"), indent=2)
    return path

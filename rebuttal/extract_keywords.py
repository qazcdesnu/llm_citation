"""Keyword extraction (GPU) -- the step the proposed method depends on.

Faithfully replicates `entity_in_contexts` + `stem_entities` from
code/code/Citations/citation.py so the extracted sets match the submitted
pipeline, and caches them so scoring runs stay CPU-only.

Ablation switches for M2:
  --extractor domain|general   E5: domain-specific NER vs a general extractor
  --no-stem                    E4: skip Porter stemming

NOTE: untested -- written on a machine without enough VRAM to load the models.
Run the self-check first:  python extract_keywords.py --self-check
"""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

# Model ids taken from the paper's footnotes 4-7.
DOMAIN_NER = {
    "disease": "alvaroalon2/biobert_diseases_ner",
    "genetic": "alvaroalon2/biobert_genetic_ner",
    "chemical": "alvaroalon2/biobert_chemical_ner",
}
GENERAL_NER = {"keyword": "yanekyuk/bert-uncased-keyword-extractor"}

_PS = PorterStemmer()
# citation.py:54 -- stopwords plus these characters
_UNWANTED = set(stopwords.words("english")) | {"]", "=", "[", "(", ")", "'", "/", "s", "-"}


def build_pipelines(kind: str, device: int = 0, dtype: str = "bfloat16"):
    import torch
    from transformers import (AutoModelForTokenClassification, AutoTokenizer,
                              pipeline)

    names = DOMAIN_NER if kind == "domain" else GENERAL_NER
    torch_dtype = getattr(torch, dtype)
    pipes = {}
    for label, name in names.items():
        model = AutoModelForTokenClassification.from_pretrained(name, torch_dtype=torch_dtype)
        tok = AutoTokenizer.from_pretrained(name)
        pipes[label] = pipeline("ner", model=model, tokenizer=tok, device=device)
    return pipes


def _merge_subwords(ner_result) -> dict[str, str]:
    """Re-joins ## subword pieces, exactly as citation.py does."""
    current, current_original, unique = "", "", {}
    for entity in ner_result:
        # citation.py checks against '0'; real pipelines emit 'O' or 'B-*'.
        # Kept verbatim so cached keywords match the submitted run.
        if entity["entity"] == "0":
            if current:
                unique[current.lower()] = current_original
                current, current_original = "", ""
            continue
        word = entity["word"]
        if word.startswith("##"):
            current += word[2:]
            current_original += word[2:]
        else:
            if current:
                unique[current.lower()] = current_original
            current, current_original = word.lower(), word
    if current:
        unique[current.lower()] = current_original
    return unique


def extract(texts: list[str], pipes, stem: bool = True) -> list[set[str]]:
    """One keyword set per input text."""
    out: list[set[str]] = [set() for _ in texts]
    for _, nlp in pipes.items():
        for idx, result in enumerate(nlp(texts)):
            unique = _merge_subwords(result)
            for lower, original in unique.items():
                if lower in _UNWANTED:
                    continue
                out[idx].add(_PS.stem(original) if stem else original)
    return out


def run(dataset: str, split_field: str, extractor: str, stem: bool,
        top_k: int, limit: int | None, out_path: Path, device: int):
    import alce_adapter as A

    items = A.load(dataset, limit=limit)
    pipes = build_pipelines(extractor, device=device)

    cache = []
    for it in items:
        sentences = A.split(it[split_field], dataset, it["question"])
        docs = it["docs"][:top_k]
        contents = [f"{d['title']} {d['text']}" for d in docs]
        cache.append({
            "sample_id": it.get("sample_id", it["question"][:64]),
            "keyword_sentences": extract(sentences, pipes, stem),
            "keyword_documents": extract(contents, pipes, stem),
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pickle.dump(cache, open(out_path, "wb"))
    print(f"wrote {len(cache)} entries -> {out_path}")


def self_check():
    """Cheap sanity run: loads the general extractor and prints keywords."""
    pipes = build_pipelines("general", device=-1)
    texts = ["Sternal plating can improve sternal stability after sternotomy.",
             "Titanium plates reduce mediastinitis after cardiac surgery."]
    for t, ks in zip(texts, extract(texts, pipes)):
        print(f"  {t}\n    -> {sorted(ks)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="asqa", choices=["asqa", "qampari"])
    ap.add_argument("--field", default="answer", help="which text to cite (answer | output)")
    ap.add_argument("--extractor", default="general", choices=["domain", "general"])
    ap.add_argument("--no-stem", action="store_true", help="E4 ablation")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--device", type=int, default=0)
    ap.add_argument("--out", default=None)
    ap.add_argument("--self-check", action="store_true")
    a = ap.parse_args()

    if a.self_check:
        return self_check()

    stem = not a.no_stem
    name = a.out or f"cache/{a.dataset}-{a.extractor}-{'stem' if stem else 'nostem'}-top{a.top_k}.pkl"
    run(a.dataset, a.field, a.extractor, stem, a.top_k, a.limit, Path(name), a.device)


if __name__ == "__main__":
    main()

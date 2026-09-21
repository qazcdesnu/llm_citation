# Reviewer's Comment

## Raw Comment

핵심 주장에 대한 실험들이 여전히 부족합니다. 예를 들어, 문장을 생성한 후, BM25로만 또는 TF-IDF로만 비교한다거나, full-token Jaccard, SPLADE 등과도 비교실험이 포함되어야 합니다. 또는 ablation study에서 각 단계별 뺐을 때, 제안한 방법들의 성능 하락이 어떻게 되는지 보여줄 필요가 있습니다. 일부 표현들, "the proposed citation method requires no neural inference"이라는 것은 적절치 않습니다. 왜냐하면 제안한 방법은 BERT/BioBERT를 돌려서 keyword를 추출하는데, 이 또한 neural inference를 사용하기 때문입니다. 그리고, 2025년도 ACL Industry 논문으로 CiteFix: Enhancing RAG Accuracy Through Post-Processing Citation Correction이 있으며, 이 방법과 비교를 할 필요가 있어 보입니다.

## Points

| No. | Problem                                                                                            | Proposed solution                                                                                                                                                              | Our solution |
| --- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| 1   | Insufficient experiments to support the core claims: no lexical/sparse baseline on the citation task | Add citation-quality (recall/precision/GPT-4) comparisons against BM25-only, TF-IDF-only, and SPLADE, run in the same post-hoc sentence→document assignment setting               | 실험 수행 |
| 2   | No experiment isolating the contribution of *keyword selection* itself                               | Add a full-token Jaccard baseline (same set-based scoring, no keyword extraction) — this is the direct control for the paper's central claim                                      | 실험 수행 |
| 3   | Lack of a stage-wise ablation study                                                                  | Ablate each pipeline stage and report the resulting drop: domain-specific NER extractor → general extractor, stemming on/off, keyword set → full tokens, top-*k* sensitivity      | 실험 수행 |
| 4   | Inappropriate expression: "requires no neural inference"                                             | Scope the claim to the matching step, since keyword extraction runs a fine-tuned BERT/BioBERT; state explicitly whether the reported efficiency numbers include that extractor    | 본문 수정 |
| 5   | Insufficient citation-related work: CiteFix (ACL 2025 Industry) not discussed                        | Cite and empirically compare against CiteFix, whose keyword-matching variant addresses the same post-hoc citation-correction task                                                 | 선행 연구 확인 |

**Our solution** uses four labels:

- **반박문 작성 필요** — nothing to change; answer in the rebuttal letter only.
- **본문 수정** — the manuscript text needs to change.
- **실험 수행** — a new experiment is required (manuscript revision follows by definition, so it is not listed separately).
- **선행 연구 확인** — prior work must be checked first (manuscript revision likewise follows).

## Manuscript evidence

Section/figure pointers for each point, so the rebuttal can be written against the actual text.

**1 — Lexical baselines are argued for in prose but never run.**
§2 distinguishes the method from sparse retrieval in four respects, explicitly naming BM25, TF-IDF, and SPLADE ("unlike BM25 and TF-IDF [21], which weight terms by frequency and inverse document frequency, we use only the intersection and union of keyword sets"). None of the three is run as a baseline. The only accuracy baseline is the dense MIPS method of the ALCE framework (`gtr-t5-large` / `gtr-t5-xxl`). Appendix C.1 does include TF-IDF, but only in a **processing-time** comparison (Jaccard 0.045 s vs. TF-IDF 0.467 s for 200 responses) — never in a citation-quality comparison. A reviewer reading §2 will expect the four distinctions to be demonstrated, not asserted.

**2 — Full-token Jaccard is the missing control.**
The paper's causal claim is that *keyword* overlap, not lexical overlap in general, tracks source lineage (§3: keyword overlap 0.21 vs. general-noun overlap 0.08 on ASQA; 0.12 / 0.05 on QAMPARI; 0.10 / 0.06 on MedDialog). That motivating experiment measures word overlap, not citation accuracy. Running the same Jaccard scoring over *all* tokens holds the set-based scoring fixed and varies only the keyword-selection step, converting the §3 observation into an end-task result.

**3 — What the paper calls an "ablation study" is a model sweep.**
Appendix B: "We conducted an ablation study to evaluate our citation method using OPT-6.7B, GPT-J 6.7B, Llama-13B, Llama2-13B, Vicuna-7B, and Mistral-7B-Instruct as shown in Table 1 and Table 4." That varies the **generator LLM**, not the components of the proposed pipeline; Appendix C.1 is titled "Processing time ablation" but likewise compares external similarity metrics on speed. Neither removes a stage of the method, which is what the reviewer is asking for. Renaming these to "model sweep" / "processing-time comparison" and adding a genuine component ablation would resolve the terminology mismatch as well as the substantive gap.

Pipeline stages available to ablate (§4): domain-specific keyword extraction (BioBERT disease/genetic/chemical NER for MedDialog, `bert-uncased-keyword-extractor` for ASQA/QAMPARI) → stemming → Jaccard similarity matrix → citation assignment.

**4 — The exact sentence the reviewer objects to.**
§2, fourth distinction: "the computation requires no neural training or inference, which yields the efficiency reported in Fig. 3 and makes the matched keyword set directly inspectable (Fig. 1)." The reviewer is correct: §4 extracts keywords with a fine-tuned BERT model, selected by domain (BioBERT NER models for MedDialog, a general-purpose extractor for ASQA/QAMPARI). The Korean abstract makes a related claim ("추가적인 학습 없이도") — that one is defensible, since no training is performed, but "inference" is not.

Two things to separate in the fix:
- *Wording.* The accurate claim is that the **similarity computation** requires no neural inference and no corpus statistics, while keyword extraction uses a lightweight encoder-only model — far cheaper than the sentence-transformer encoders it is compared against.
- *Measurement.* Fig. 3 reports "loading the model and performing inference", which for the proposed method should mean the keyword extractor itself. If so, the 20.6× speedup and 17.9× memory reduction already account for the NER cost and the claim survives once reworded. This should be stated explicitly in the caption — otherwise the reviewer will read the efficiency numbers as excluding the very step they flagged.

*Label note:* **본문 수정** assumes Fig. 3's "Load Model / Inference" bars already time the keyword extractor. If they do not, the figure has to be re-measured with the extractor included and this row becomes **실험 수행**. Worth confirming before the rebuttal is written.

**5 — CiteFix overlaps more than a citation.**
*CiteFix: Enhancing RAG Accuracy Through Post-Processing Citation Correction* (Maheshwari, Tenneti, Nakkiran; ACL 2025 Industry Track; arXiv:2504.15629) targets the same task — correcting citations after generation — and its method family includes **keyword matching plus semantic matching**, alongside BERTScore-based and lightweight-LLM variants. It reports a 15.46% relative improvement in overall citation accuracy. Because one of its variants instantiates the same core idea as this paper, treating it only as a related-work citation is unlikely to satisfy the reviewer; a head-to-head comparison on at least one shared dataset is the safer response. Note also that CiteFix is concurrent industry work rather than a prior baseline, which is worth stating when positioning the contribution.

*Label note:* **선행 연구 확인** covers reading CiteFix and positioning it against our method in related work. If, after reading it, we judge that the reviewer wants numbers rather than discussion — and CiteFix's setup can be reproduced on one of our datasets — this row escalates to **실험 수행**.

## References

- CiteFix (ACL Anthology): https://aclanthology.org/2025.acl-industry.23/
- CiteFix (arXiv): https://arxiv.org/abs/2504.15629
- SPLADE [16], BM25 [20], TF-IDF [21] — already in the manuscript's bibliography

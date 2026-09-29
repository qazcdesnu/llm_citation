### ASQA

| Method | Citation Recall | Citation Precision | F1 |
| --- | ---: | ---: | ---: |
| Dense MIPS (gtr-t5-xxl) — baseline | 56.3 | 56.3 | 56.3 |
| Keyword Jaccard — proposed | 53.3 | 53.3 | 53.3 |
| Keyword Jaccard — proposed (threshold 0.2) | 51.8 | 51.8 | 51.8 |
| E1 full-token Jaccard | 56.1 | 56.1 | 56.1 |
| E2 CiteFix §3.1 | 55.3 | 55.3 | 55.3 |
| E3 CiteFix §3.2 KSC | 55.1 | 55.1 | 55.1 |
| E7 TF-IDF | 52.3 | 52.3 | 52.3 |
| E8 BM25 | 48.6 | 48.6 | 48.6 |
| Generator's own in-context citations (reference) | 56.0 | 50.0 | 52.8 |
| ALCE post_hoc_cite gtr-t5-xxl (reference) | 56.3 | 56.3 | 56.3 |

### QAMPARI

| Method | Citation Recall | Citation Precision | F1 |
| --- | ---: | ---: | ---: |
| Dense MIPS (gtr-t5-xxl) — baseline | 14.0 | 14.0 | 14.0 |
| Keyword Jaccard — proposed | 10.8 | 10.8 | 10.8 |
| Keyword Jaccard — proposed (threshold 0.2) | 10.6 | 11.0 | 10.8 |
| E1 full-token Jaccard | 10.2 | 10.2 | 10.2 |
| E2 CiteFix §3.1 | 12.7 | 12.7 | 12.7 |
| E3 CiteFix §3.2 KSC | 12.9 | 12.9 | 12.9 |
| E7 TF-IDF | 13.8 | 13.8 | 13.8 |
| E8 BM25 | 13.3 | 13.3 | 13.3 |
| Generator's own in-context citations (reference) | 10.6 | 10.9 | 10.8 |
| ALCE post_hoc_cite gtr-t5-xxl (reference) | 14.0 | 14.0 | 14.0 |


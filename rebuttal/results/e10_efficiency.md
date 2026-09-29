E10 on appendix_data.pkl: 200 responses, 969 sentences, 3876 sentence-document pairs. GPU NVIDIA GeForce RTX 3090, median of 3 runs.

| Method | Device | Model load (s) | Load peak GPU (MB) | Inference, 200 responses (s) | ms / sentence | Inference peak GPU (MB) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| keyword_jaccard (as Fig. 6: keywords precomputed) | cpu | 0.00 | 0 | 0.003 | 0.003 | 0 |
| keyword_jaccard + extraction (domain) | gpu | 5.59 | 640 | 23.605 | 24.360 | 673 |
| keyword_jaccard + extraction (general) | gpu | 1.39 | 223 | 7.719 | 7.966 | 247 |
| full_token_jaccard | cpu | 0.00 | 0 | 1.023 | 1.056 | 0 |
| citefix_intersection | cpu | 0.00 | 0 | 0.018 | 0.018 | 0 |
| citefix_ksc | cpu | 0.00 | 0 | 0.026 | 0.027 | 0 |
| tfidf | cpu | 0.00 | 0 | 0.411 | 0.424 | 0 |
| bm25 | cpu | 0.00 | 0 | 0.335 | 0.346 | 0 |
| dense gtr-t5-xxl | gpu | 11.42 | 18569 | 175.120 | 180.723 | 19851 |
| dense gtr-t5-large | gpu | 5.65 | 1290 | 14.650 | 15.118 | 1438 |
| splade (SPLADE++) | gpu | 1.49 | 428 | 5.638 | 5.818 | 603 |

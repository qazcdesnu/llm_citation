# rebuttal/

Code written for the reviewer response. The original submission code under
`code/code/` is left untouched so it stays a faithful record of what was
submitted.

| File | Purpose |
| --- | --- |
| `baselines.py` | One scoring interface for every method under comparison (proposed, E1, E2, E3, E7, E8), plus the shared calibration and assignment path |
| `run_smoke.py` | M1 check: runs every scorer on `appendix_data.pkl`, reports timing and assignment agreement |
| `smoke_results.txt` | Output of the above, committed for the record |
| `alce_adapter.py` | Converts our citation assignments into the result JSON that ALCE's `eval.py` scores |
| `extract_keywords.py` | GPU: BioBERT/BERT keyword extraction, cached so scoring stays CPU-only. E4/E5 ablation switches |
| `measure_efficiency.py` | E10/E11: the fair efficiency re-measurement for Point 4 |
| `run_experiments.py` | Orchestrator: build citation files, then score them with ALCE |
| `requirements.txt` | Environment |
| `SERVER.md` | **Hardware requirements and the run order for the GPU server** |

## Verification status

CPU paths (`baselines.py`, `alce_adapter.py`, `run_experiments.py --build`) are
verified on real ASQA/QAMPARI data. GPU paths (`extract_keywords.py`,
`measure_efficiency.py`, `run_experiments.py --eval`) are **unverified** -- this
machine has 8GB of VRAM and 31GB of free disk, and the AutoAIS checkpoint alone
is 45.5GB.

## Naming note

`citation.py:82` calls the full-token baseline `causal_jaccard`, which is a
misnomer -- there is nothing causal about it. This module uses
`full_token_jaccard`. The original name is left in place so the submitted code
still matches the paper.

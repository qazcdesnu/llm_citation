# rebuttal/

Code written for the reviewer response. The original submission code under
`code/code/` is left untouched so it stays a faithful record of what was
submitted.

| File | Purpose |
| --- | --- |
| `baselines.py` | One scoring interface for every method under comparison (proposed, E1, E2, E3, E7, E8), plus the shared calibration and assignment path |
| `run_smoke.py` | M1 check: runs every scorer on `appendix_data.pkl`, reports timing and assignment agreement |
| `smoke_results.txt` | Output of the above, committed for the record |
| `requirements.txt` | CPU-only environment |

## Naming note

`citation.py:82` calls the full-token baseline `causal_jaccard`, which is a
misnomer -- there is nothing causal about it. This module uses
`full_token_jaccard`. The original name is left in place so the submitted code
still matches the paper.

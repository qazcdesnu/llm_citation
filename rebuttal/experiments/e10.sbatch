#!/bin/bash
# E10: re-measure Fig. 6 (Appendix C.1) on the same 200 PubMedQA responses,
# with keyword extraction inside the timing, against every rebuttal baseline.
# Submit from rebuttal/:   sbatch experiments/e10.sbatch
#SBATCH --job-name=e10
#SBATCH --partition=P2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1                 # timing only; gtr-t5-xxl fp32 (~19GB) fits one 24GB card
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=03:00:00
#SBATCH --output=slurm_log/%x-%j.out
#SBATCH --open-mode=append
#SBATCH --exclude=b01

set -euo pipefail

REPO=$(pwd)
export HF_HOME=/shared/s3/lab03/jinwoongkim/hf_cache
source ${HOME}/miniconda3/bin/activate llmcite

echo "== start $(date -Is) on $(hostname)"
nvidia-smi --query-gpu=name,memory.total --format=csv
lscpu | grep -m1 "Model name"

python measure_efficiency.py --repeats 3 --out results/e10_efficiency.json

python - <<'EOF'
import json
r = json.load(open("results/e10_efficiency.json"))
lines = [f"E10 on {r['data']}: {r['responses']} responses, {r['sentences']} sentences, "
         f"{r['pairs']} sentence-document pairs. GPU {r['env']['gpu']}, median of {r['env']['repeats']} runs.", "",
         "| Method | Device | Model load (s) | Load peak GPU (MB) | Inference, 200 responses (s) | ms / sentence | Inference peak GPU (MB) |",
         "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
for name, m in r["methods"].items():
    lines.append(f"| {name} | {m['device']} | {m['load_seconds']:.2f} | {m['load_peak_gpu_mb']:.0f} | "
                 f"{m['inference_seconds']:.3f} | {m['ms_per_sentence']:.3f} | {m['inference_peak_gpu_mb']:.0f} |")
open("results/e10_efficiency.md", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
EOF
echo "== done $(date -Is)"

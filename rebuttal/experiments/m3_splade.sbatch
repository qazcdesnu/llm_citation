#!/bin/bash
# M3 / E9: SPLADE citation baseline on the same M2 generations (Llama2-7B Chat, 100 each).
# Adds splade files to runs/m2 so the M2 table gains one row per dataset.
# Submit from rebuttal/:   sbatch experiments/m3_splade.sbatch
#SBATCH --job-name=m3-splade
#SBATCH --partition=P2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:2                 # AutoAIS scoring
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=03:00:00
#SBATCH --output=slurm_log/%x-%j.out
#SBATCH --open-mode=append
#SBATCH --exclude=b01

set -euo pipefail

REPO=$(pwd)
WORK=/shared/s3/lab03/jinwoongkim
export HF_HOME=$WORK/hf_cache
export ALCE_DIR=$WORK/ALCE
set -a; source "$REPO/../.env"; set +a
export HF_TOKEN=${HUGGING_FACE_HUB_TOKEN:-}
source ${HOME}/miniconda3/bin/activate llmcite

RUNS=$WORK/runs/m2
REF=$WORK/runs/m2_ref
step() { echo; echo "== [$1] $(date -Is)"; }

step "sanity"
python - <<'EOF'
import numpy as np
from baselines import SCORERS, Context
docs = ["The Eiffel Tower is a wrought-iron lattice tower in Paris, France.",
        "Mount Everest is Earth's highest mountain above sea level, in the Himalayas.",
        "The Great Barrier Reef is the world's largest coral reef system, off Australia."]
sents = ["Everest is the tallest peak on Earth.", "The reef lies off the coast of Queensland.",
         "Gustave Eiffel's company built the tower in Paris."]
m = SCORERS["splade"](sents, docs, Context())
print(np.round(m, 2)); print("argmax", m.argmax(1))
assert list(m.argmax(1)) == [1, 2, 0], "SPLADE sanity check failed"
print("SPLADE sanity OK")
EOF

step build
for DS in asqa qampari; do
    RES=$ALCE_DIR/result/${DS}-Llama-2-7b-chat-hf-gtr-shot2-ndoc5-42-quick_test100.json
    python run_experiments.py --build --datasets $DS --result "$DS=$RES" --runs-dir "$RUNS" \
        --methods splade --threshold 0.0
done

step eval
python run_experiments.py --eval --runs-dir "$RUNS"      # scores only files without .score

step summarize
python summarize_scores.py --runs-dir "$RUNS" --extra "$REF" --out "$REPO/results/m2_scores.md"
step done

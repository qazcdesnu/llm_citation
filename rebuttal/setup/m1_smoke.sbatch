#!/bin/bash
# M1 smoke test: Llama2-7B Chat generation via ALCE run.py (transformers 5.x compat),
# re-citation through alce_adapter, and AutoAIS scoring on 2 GPUs.
# Submit from rebuttal/:   sbatch setup/m1_smoke.sbatch
# Each step reports PASS/FAIL and the job keeps going, so one run shows every break.
#SBATCH --job-name=m1-smoke
#SBATCH --partition=P2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:2                 # AutoAIS T5-XXL bf16 ~22GB -> two 24GB cards
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G                    # T5-XXL fp32 shards (45.5GB) pass through CPU RAM
#SBATCH --time=03:00:00
#SBATCH --output=slurm_log/%x-%j.out
#SBATCH --open-mode=append
#SBATCH --exclude=b01

set -uo pipefail

REPO=$(pwd)   # rebuttal/
WORK=/shared/s3/lab03/jinwoongkim
export HF_HOME=$WORK/hf_cache
export ALCE_DIR=$WORK/ALCE
set -a; source "$REPO/../.env"; set +a      # HUGGING_FACE_HUB_TOKEN (gated Llama-2)
export HF_TOKEN=${HUGGING_FACE_HUB_TOKEN:-}
source ${HOME}/miniconda3/bin/activate llmcite

N=3
MODEL=meta-llama/Llama-2-7b-chat-hf
SMOKE=$WORK/smoke
mkdir -p "$SMOKE"

step() { echo; echo "== [$1] $(date -Is)"; }
report() { if [ "$1" -eq 0 ]; then echo "PASS: $2"; else echo "FAIL($1): $2"; fi; }

step env
nvidia-smi --query-gpu=index,name,memory.total,memory.used --format=csv
python -c "import torch, transformers; print('torch', torch.__version__, '| transformers', transformers.__version__, '| gpus', torch.cuda.device_count())"

# 1) generation -- VANILLA (5 docs in prompt, 2-shot), model overridden to 7B chat
for DS in asqa qampari; do
    step "generate $DS"
    (cd "$ALCE_DIR" && python run.py --config configs/${DS}_llama2_shot2_ndoc5_gtr_default.yaml \
        --model $MODEL --quick_test $N --seed 42)
    report $? "run.py $DS"
done
ls -l "$ALCE_DIR"/result/*Llama-2-7b-chat-hf*quick_test$N*.json 2>/dev/null
ASQA_RES=$(ls "$ALCE_DIR"/result/asqa-Llama-2-7b-chat-hf-*quick_test$N.json 2>/dev/null | head -1)
QAMP_RES=$(ls "$ALCE_DIR"/result/qampari-Llama-2-7b-chat-hf-*quick_test$N.json 2>/dev/null | head -1)
[ -n "$ASQA_RES" ] && python - "$ASQA_RES" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))["data"]
for it in d:
    print("Q:", it["question"][:80]); print("A:", str(it["output"])[:300]); print("docs:", len(it["docs"]))
EOF

# 2) re-cite the generated answers (CPU method) with alce_adapter
step "adapter build"
if [ -z "$ASQA_RES" ] || [ -z "$QAMP_RES" ]; then echo "FAIL: no run.py result to re-cite"; step done; exit 1; fi
python - "$ASQA_RES" "$QAMP_RES" "$SMOKE" <<'EOF'
import sys, json
from pathlib import Path
sys.path.insert(0, ".")
import alce_adapter as A
out = Path(sys.argv[3])
for ds, res in [("asqa", sys.argv[1]), ("qampari", sys.argv[2])]:
    payload, dropped = A.build(ds, "bm25", text_field="output", result=res)
    p = A.write(payload, out, f"{ds}-gen-bm25-smoke")
    print(ds, "items", len(payload["data"]), "dropped", dropped, "->", p)
    print("  ", payload["data"][0]["output"][:200])
EOF
report $? "alce_adapter build"

# 3) AutoAIS scoring on 2 GPUs: the generator's own citations and our re-citation
for F in "$ASQA_RES" "$SMOKE/asqa-gen-bm25-smoke.json" "$QAMP_RES" "$SMOKE/qampari-gen-bm25-smoke.json"; do
    [ -f "$F" ] || { echo "skip missing $F"; continue; }
    step "eval $(basename "$F")"
    (cd "$ALCE_DIR" && python eval.py --f "$F" --citations)
    report $? "eval.py --citations $(basename "$F")"
    [ -f "$F.score" ] && cat "$F.score"
done
nvidia-smi --query-gpu=index,memory.used --format=csv

step done

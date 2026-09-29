#!/bin/bash
# M2 (+ E7/E8): ASQA/QAMPARI, Llama2-7B Chat generated answers, 100 each (quick_test 100, seed 42).
# Every method re-cites the same answers over the same 5 prompt docs; ALCE eval.py scores citations.
#   baseline dense (gtr-t5-xxl), proposed (threshold 0 and paper's 0.2), E1, E2, E3, E7, E8
# Submit from rebuttal/:   sbatch experiments/m2.sbatch
# Idempotent: existing generations, keyword caches and .score files are reused.
#SBATCH --job-name=m2
#SBATCH --partition=P2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:2                 # AutoAIS T5-XXL bf16 ~22GB -> two 24GB cards
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G
#SBATCH --time=10:00:00
#SBATCH --output=slurm_log/%x-%j.out
#SBATCH --open-mode=append
#SBATCH --exclude=b01

set -euo pipefail

REPO=$(pwd)   # rebuttal/
WORK=/shared/s3/lab03/jinwoongkim
export HF_HOME=$WORK/hf_cache
export ALCE_DIR=$WORK/ALCE
set -a; source "$REPO/../.env"; set +a
export HF_TOKEN=${HUGGING_FACE_HUB_TOKEN:-}
source ${HOME}/miniconda3/bin/activate llmcite

MODEL=meta-llama/Llama-2-7b-chat-hf
N=100; SEED=42
RUNS=$WORK/runs/m2
mkdir -p "$RUNS" "$REPO/results"
step() { echo; echo "== [$1] $(date -Is)"; }

step env
nvidia-smi --query-gpu=index,name,memory.total --format=csv
python -c "import torch, transformers; print('torch', torch.__version__, '| transformers', transformers.__version__, '| gpus', torch.cuda.device_count())"

# 1) generation (VANILLA: 5 docs in prompt, 2-shot; same config family as the smoke test)
declare -A RES
for DS in asqa qampari; do
    RES[$DS]=$ALCE_DIR/result/${DS}-Llama-2-7b-chat-hf-gtr-shot2-ndoc5-${SEED}-quick_test${N}.json
    if [ ! -f "${RES[$DS]}" ]; then
        step "generate $DS"
        (cd "$ALCE_DIR" && python run.py --config configs/${DS}_llama2_shot2_ndoc5_gtr_default.yaml \
            --model $MODEL --quick_test $N --seed $SEED)
    fi
    python -c "import json,sys; d=json.load(open(sys.argv[1]))['data']; print('$DS items', len(d))" "${RES[$DS]}"
done

# 2) keyword caches for the proposed method (general extractor, as in the paper for ASQA/QAMPARI)
for DS in asqa qampari; do
    CACHE=$REPO/cache/${DS}-gen-general-stem-top5.pkl
    if [ ! -f "$CACHE" ]; then
        step "keywords $DS"
        python extract_keywords.py --dataset $DS --extractor general --result "${RES[$DS]}" --out "$CACHE"
    fi
done

# 3) citation files -- threshold 0 (always cite the argmax doc) for every method
step build
BASE="dense_gtr_xxl,full_token_jaccard,citefix_intersection,citefix_ksc,tfidf,bm25"
for DS in asqa qampari; do
    python run_experiments.py --build --datasets $DS --result "$DS=${RES[$DS]}" --runs-dir "$RUNS" \
        --methods $BASE --threshold 0.0
    for TH in 0.0 0.2; do   # proposed: like-for-like (0) and the paper's setting (0.2)
        python run_experiments.py --build --datasets $DS --result "$DS=${RES[$DS]}" --runs-dir "$RUNS" \
            --methods keyword_jaccard --keyword-cache "$REPO/cache/${DS}-gen-general-stem-top5.pkl" \
            --threshold $TH
    done
done

# 4) references: ALCE's official post-hoc dense citation, and the generator's own citations
REF=$WORK/runs/m2_ref
mkdir -p "$REF"
for DS in asqa qampari; do
    step "post_hoc_cite $DS"
    OUT="${RES[$DS]}.post_hoc_cite.gtr-t5-xxl-overwrite"
    [ -f "$OUT" ] || (cd "$ALCE_DIR" && python post_hoc_cite.py --f "${RES[$DS]}" --retriever gtr-t5-xxl --overwrite)
    [ -f "$REF/${DS}-post_hoc_cite-gtr-t5-xxl.json" ] || cp "$OUT" "$REF/${DS}-post_hoc_cite-gtr-t5-xxl.json"
    [ -f "$REF/${DS}-generator-own-citations.json" ] || cp "${RES[$DS]}" "$REF/${DS}-generator-own-citations.json"
done

# 5) scoring
step "eval runs"
python run_experiments.py --eval --runs-dir "$RUNS"
step "eval references"
python run_experiments.py --eval --runs-dir "$REF"
step "answer quality (identical text for every method; scored once)"
AQ=$WORK/runs/m2_answer_quality/asqa-answer-quality.json
mkdir -p "$(dirname "$AQ")"
[ -f "$AQ" ] || cp "${RES[asqa]}" "$AQ"
[ -f "$AQ.score" ] || (cd "$ALCE_DIR" && python eval.py --f "$AQ" --qa)
cat "$AQ.score"

# 6) table
step summarize
python summarize_scores.py --runs-dir "$RUNS" --extra "$REF" --out "$REPO/results/m2_scores.md"
step done

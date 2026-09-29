#!/bin/bash
# M1: build the llmcite env, install ALCE + data, and verify GPU/imports.
# Submit from rebuttal/:   mkdir -p slurm_log && sbatch setup/setup_env.sbatch
# Idempotent: an existing env / ALCE checkout / data dir is reused.
#SBATCH --job-name=llmcite-setup
#SBATCH --partition=P2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1                 # only for the CUDA check at the end
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=03:00:00
#SBATCH --output=slurm_log/%x-%j.out
#SBATCH --open-mode=append
#SBATCH --exclude=b01

set -euo pipefail

WORK=/shared/s3/lab03/jinwoongkim
export HF_HOME=$WORK/hf_cache
export PIP_CACHE_DIR=$WORK/pip_cache
export ALCE_DIR=$WORK/ALCE
mkdir -p "$HF_HOME" "$PIP_CACHE_DIR"
REPO=$(pwd)   # rebuttal/

echo "== start $(date -Is) on $(hostname)"
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv
nvidia-smi | grep -m1 "CUDA Version" || true

# ~/.bashrc has no conda init, so activate by sourcing (see SERVER.md)
source ${HOME}/miniconda3/bin/activate

# conda-forge only: avoids the Anaconda default-channel ToS prompt in batch jobs
if ! conda env list | grep -qE '^llmcite\s'; then
    echo "== creating env llmcite"
    conda create -y -n llmcite --override-channels -c conda-forge python=3.11
fi
conda activate llmcite
python --version

echo "== pip install $(date -Is)"
python -m pip install --upgrade pip
python -m pip install -r "$REPO/requirements.txt"
python -c "import nltk; [nltk.download(p, quiet=True) for p in ('stopwords','punkt','punkt_tab')]"

echo "== ALCE $(date -Is)"
if [ ! -d "$ALCE_DIR/.git" ]; then
    git clone https://github.com/princeton-nlp/ALCE.git "$ALCE_DIR"
fi
if [ ! -f "$ALCE_DIR/data/asqa_eval_gtr_top100.json" ]; then
    (cd "$ALCE_DIR" && bash download_data.sh)
fi
git -C "$ALCE_DIR" log --oneline -1
ls "$ALCE_DIR/data" | head -20
du -sh "$ALCE_DIR/data"

echo "== verify $(date -Is)"
python - <<'EOF'
import importlib, torch
print("torch", torch.__version__, "| cuda build", torch.version.cuda,
      "| available", torch.cuda.is_available(),
      "| device", torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
x = torch.randn(1024, 1024, device="cuda"); print("matmul ok:", float((x @ x).sum()) == float((x @ x).sum()))
for m in ["transformers", "accelerate", "sentence_transformers", "sentencepiece", "rouge_score",
          "mauve", "sklearn", "rank_bm25", "nltk", "pandas", "numpy", "langchain_core", "yaml", "openai"]:
    mod = importlib.import_module(m)
    print(f"  {m:22s} {getattr(mod, '__version__', 'ok')}")
EOF

# rebuttal/ code paths that need no model download
cd "$REPO"
python -c "import alce_adapter as A; print('ALCE_DIR', A.ALCE_DIR); print('asqa items', len(A.load('asqa')))"
python run_experiments.py --eval --dry-run | head -5 || true

python -m pip freeze > "$REPO/setup/pip-freeze.txt"
echo "== done $(date -Is)"

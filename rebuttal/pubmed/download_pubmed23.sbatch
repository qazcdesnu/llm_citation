#!/bin/bash
# PubMed 2023 baseline download (network/IO only -- no GPU requested).
# Submit from rebuttal/:   mkdir -p slurm_log && sbatch pubmed/download_pubmed23.sbatch
# Resumable: verified files are skipped, so resubmit if it hits the time limit.
#SBATCH --job-name=pubmed23-dl
#SBATCH --partition=P2
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=12:00:00
#SBATCH --output=slurm_log/%x-%j.out
#SBATCH --open-mode=append
#SBATCH --exclude=b01

set -euo pipefail

# stdlib-only script, so the base env is enough
source ${HOME}/miniconda3/bin/activate

OUT=/shared/s3/lab03/jinwoongkim/pubmed/baseline23

echo "start $(date -Is) on $(hostname)"
python pubmed/download_pubmed23.py --out "$OUT" --workers 3
echo "end $(date -Is)"
du -sh "$OUT"

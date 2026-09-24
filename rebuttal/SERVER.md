# 서버 실행 가이드 (GSDS 서버, 24GB GPU 기준)

이 디렉터리의 코드는 **로컬(RTX 4060 Laptop 8GB)에서 GPU 부분을 실행할 수 없어** CPU 경로만 검증된 상태입니다.
CPU 경로(`baselines.py`, `alce_adapter.py`, `run_experiments.py --build`)는 ASQA/QAMPARI 실데이터로 동작을 확인했고,
GPU 경로(`extract_keywords.py`, `measure_efficiency.py`, `run_experiments.py --eval`)는 **미검증**입니다.

실행 대상은 GSDS 서버입니다. 서버에는 **24GB GPU만 있습니다**: `P2` 파티션은 RTX 3090, `P3` 파티션은 RTX 4090입니다.
48GB나 80GB GPU는 없습니다. 서버 사용 규칙은 `../about-server/slurm-gpu-guide.md`를 참고하십시오.
특히 **로그인 노드에서는 실행하지 말고**, `--mem`을 반드시 지정하며, **작업당 최대 12시간**입니다.

## 1. 왜 GPU가 필요한가

ALCE에는 gold citation 라벨이 없습니다. `citation_rec` / `citation_prec`는
`google/t5_xxl_true_nli_mixture`(T5-XXL, 11B)로 문장마다 NLI를 돌려 계산합니다.
즉 평가 자체가 대형 모델 추론입니다.

## 2. 요구 사양 (24GB GPU 기준)

| 단계 | 모델 | VRAM | 24GB에서 |
| --- | --- | --- | --- |
| **AutoAIS 채점** (`eval.py --citations`) | t5_xxl_true_nli_mixture 11B | **bf16 ≈ 22GB** | **GPU 2장 권장** (아래 참고) |
| Fig. 3 비교 대상 (E11) | gtr-t5-xxl (4.8B) | fp32 ≈ 19GB | 1장 |
| 답변 생성 (선택) | Llama2-13B 등 | fp16 ≈ 26GB | 2장 (`device_map="auto"`). 7B급(14GB)은 1장 |
| Keyword 추출 | BioBERT NER ×3 / BERT-base | < 2GB | 1장 (CPU로도 가능) |
| dense baseline | gtr-t5-large | ≈ 1.5GB | 1장 |

**AutoAIS를 24GB에서 돌리는 방법**
ALCE `utils.py`의 `get_max_memory()`는 GPU마다 `여유 VRAM − 6GB`를 모델 적재 예산으로 잡습니다.
24GB 카드 한 장이면 예산이 약 17GB라서 22GB 모델이 들어가지 않습니다.

- **(권장) GPU 2장: `--gres=gpu:2`**
  예산이 2 × ~17GB ≈ 34GB가 되어 **ALCE 코드를 수정하지 않고** 두 장에 나눠 올라갑니다.
  원본 채점 코드를 그대로 쓰므로 수치 재현성 측면에서도 안전합니다.
- **GPU 1장**
  `get_max_memory()`에서 `free_in_GB-6`을 `free_in_GB-1` 정도로 완화해야 합니다.
  이 경우 activation 여유가 1–2GB뿐이라 긴 입력에서 OOM이 날 수 있습니다. 대기열이 길어 2장을 받기 어려울 때만 사용하십시오.
- **8-bit / 4-bit 양자화는 쓰지 마십시오.** 논문의 기존 수치와 직접 비교할 수 없습니다.

> `get_max_memory()`의 동작은 ALCE를 clone한 뒤 `utils.py`에서 한 번 확인하십시오.
> 이 파일은 로컬 코드 기준으로 작성되었고, 서버에는 아직 ALCE가 없습니다.

**디스크**: AutoAIS 체크포인트만 **45.5GB**(fp32 5샤드)이고, gtr-t5-xxl 19GB, NER 1.5GB입니다.
생성 모델까지 받으면 총 **160GB+** 입니다. 개인 홈 quota는 **100GB**이므로
**모델 캐시와 ALCE 데이터는 랩 공용 디렉토리(`/shared/s3/lab03`, 10TB)에 두십시오** (§3의 0번 단계).

**예상 소요**: ASQA 948건 기준 설정 하나당 NLI 호출이 약 7,000회입니다.
A6000 bf16 기준으로 설정당 30–60분을 추정했습니다. 3090 2장에 나눠 올리면 GPU 간 전송 때문에 이보다 느릴 수 있습니다.
6개 방법 × 2개 데이터셋이면 **총 6–12시간 이상**이므로 **12시간 제한 안에 한 번에 끝난다고 가정하지 마십시오.**
`run_experiments.py --eval`은 이미 채점된 파일(`*.json.score`)을 건너뛰므로,
시간 초과로 끊겨도 **같은 작업을 다시 제출하면 이어서 진행됩니다** (중단 시점에 채점 중이던 파일 하나만 처음부터 다시 합니다).

## 3. 실행 순서

모든 단계는 GPU 노드에서 실행합니다. 환경 설치도 로그인 노드가 아니라 `srun`이나 `launch-shell` 안에서 합니다.

```bash
# 0) 캐시·데이터를 공용 디렉토리로 (~/.bashrc에 추가 권장)
export WORK=/shared/s3/lab03/$USER
mkdir -p $WORK/{hf_cache,pip_cache}
export HF_HOME=$WORK/hf_cache
export PIP_CACHE_DIR=$WORK/pip_cache

# 환경 (GPU 노드에서)
srun -p P2 --gres=gpu:1 --cpus-per-task=4 --mem=16G --time=01:00:00 --pty bash
conda create -n llmcite python=3.11 -y && conda activate llmcite
pip install -r requirements.txt
pip install torch transformers sentence-transformers accelerate   # GPU 추가분
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('punkt_tab')"

# 1) ALCE 데이터 (이미 받았다면 생략). 공용 디렉토리에 둔다
git clone https://github.com/princeton-nlp/ALCE.git $WORK/ALCE && cd $WORK/ALCE && bash download_data.sh

# 2) 동작 확인 (GPU 1장)
python extract_keywords.py --self-check

# 3) keyword 캐시 생성: 제안 방법 및 E4/E5 ablation (GPU 1장)
python extract_keywords.py --dataset asqa    --extractor general              # 기본
python extract_keywords.py --dataset asqa    --extractor general --no-stem    # E4
python extract_keywords.py --dataset asqa    --extractor domain               # E5
python extract_keywords.py --dataset qampari --extractor general

# 4) 인용 파일 생성 (CPU만 필요. srun 할당 시 --gres 없이)
python run_experiments.py --build \
    --methods full_token_jaccard,citefix_intersection,citefix_ksc,tfidf,bm25
python run_experiments.py --build --datasets asqa --methods keyword_jaccard \
    --keyword-cache cache/asqa-general-stem-top5.pkl

# 5) 채점: GPU 2장, sbatch로 제출 (아래 스크립트)
sbatch eval.sbatch

# 6) 효율성 재측정 (E10 / E11), GPU 1장
python measure_efficiency.py --dataset asqa --limit 200
```

5단계용 `eval.sbatch` 예시입니다(`rebuttal/`에서 제출):

```bash
#!/bin/bash
#SBATCH --job-name=llmcite-eval
#SBATCH --partition=P2
#SBATCH --nodes=1
#SBATCH --gres=gpu:2                 # AutoAIS 11B를 두 장에 분산 (ALCE 코드 수정 불필요)
#SBATCH --cpus-per-task=8
#SBATCH --mem=96G                    # fp32 체크포인트(45.5GB)를 로드하는 동안 CPU RAM 여유 필요
#SBATCH --time=12:00:00
#SBATCH --output=slurm_log/%x-%j.out
#SBATCH --open-mode=append

source ${HOME}/.bashrc
conda activate llmcite
export HF_HOME=/shared/s3/lab03/$USER/hf_cache

python run_experiments.py --eval --alce /shared/s3/lab03/$USER/ALCE
```

- 12시간 안에 끝나지 않으면 같은 스크립트를 다시 `sbatch`로 제출합니다. 자동으로 이어서 하려면 `about-server/slurm-gpu-guide.md` §5의 requeue 패턴을 쓰십시오.
- 제출 전에 `mkdir -p slurm_log`를 실행하십시오. 디렉터리가 없으면 로그가 남지 않습니다.
- `--mem=96G`는 추정치입니다. 첫 실행 후 `sacct -j <id> --format=MaxRSS`로 실제 사용량을 보고 줄이십시오.

`--alce` 경로는 기본값이 `~/Desktop/gsds/Research/ALCE`이므로 서버에서는 반드시 지정하십시오.

**효율성 측정(E10/E11) 주의**: 논문 Fig. 3의 기존 수치는 A6000에서 측정했습니다.
서버의 3090/4090에서 잰 시간이나 메모리를 기존 수치와 섞지 말고, **비교 대상 전부를 같은 GPU에서 다시 측정**하십시오.
결과에는 GPU 모델을 함께 기록하십시오(`P2`=3090, `P3`=4090).
gtr-t5-xxl(fp32 19GB)은 24GB 한 장에 들어갑니다.

## 4. 서버에서 먼저 확인할 것

1. `python extract_keywords.py --self-check`: NER 파이프라인이 로드되고 키워드가 뽑히는지 확인
2. GPU 노드 안에서 `nvidia-smi`로 할당받은 GPU 수와 여유 VRAM 확인 (로그인 노드에는 `nvidia-smi`가 없습니다)
3. `df -h /shared/s3/lab03`와 `du -sh ~`: 공용 디렉토리 여유와 홈 사용량(quota 100GB) 확인
4. `echo $HF_HOME`: 모델이 홈이 아닌 공용 디렉토리에 받아지는지 확인
5. `run_experiments.py --eval --dry-run --alce <경로>`로 명령만 먼저 출력해 경로 확인
6. 파일 하나로 AutoAIS가 2장에 적재되고 OOM 없이 도는지 짧게 확인한 뒤 전체 채점 제출

## 5. 남은 설계 결정

- **`--field` 선택**: 현재 기본값은 `answer`(ALCE gold 장문 답변)입니다. 생성기 변동성을 제거해
  인용 방법만 비교하는 설정이라 깔끔하지만, 논문의 기존 프로토콜은 생성된 답변을 씁니다.
  기존 Table 1·4와 같은 축에서 비교하려면 생성 답변(`--field output`)이 필요하고, 그러면 생성 단계도 서버에서 돌려야 합니다.
  13B 생성은 24GB GPU 2장, 7B급은 1장이 필요합니다.
- **temperature / threshold sweep**: 방법별 최적값을 dev subset에서 정한 뒤 본 실행에 적용해야 합니다
  (`--temperature`, `--threshold`). 현재 기본값은 원본 코드의 값일 뿐 공정한 비교값이 아닙니다.

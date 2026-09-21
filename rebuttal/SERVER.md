# 서버 실행 가이드

이 디렉터리의 코드는 **로컬(RTX 4060 Laptop 8GB)에서 GPU 부분을 실행할 수 없어** CPU 경로만 검증된 상태입니다.
CPU 경로(`baselines.py`, `alce_adapter.py`, `run_experiments.py --build`)는 ASQA/QAMPARI 실데이터로 동작을 확인했고,
GPU 경로(`extract_keywords.py`, `measure_efficiency.py`, `run_experiments.py --eval`)는 **미검증**입니다.

## 1. 왜 GPU가 필요한가

ALCE에는 gold citation 라벨이 없습니다. `citation_rec` / `citation_prec`는
`google/t5_xxl_true_nli_mixture`(T5-XXL, 11B)로 문장마다 NLI를 돌려 계산합니다.
즉 평가 자체가 대형 모델 추론입니다.

## 2. 요구 사양

| 단계 | 모델 | VRAM | 비고 |
| --- | --- | --- | --- |
| **AutoAIS 채점** (`eval.py --citations`) | t5_xxl_true_nli_mixture 11B | **bf16 ≈ 22GB** | ALCE `get_max_memory()`가 `free−6GB`를 예산으로 잡으므로 **여유 28GB+ 권장** |
| Fig. 3 비교 대상 (E11) | gtr-t5-xxl (4.8B) | fp32 ≈ 19GB | 논문이 비교한 sentence transformer |
| 답변 생성 (선택) | Llama2-13B 등 | fp16 ≈ 26GB | 7B급은 14GB |
| Keyword 추출 | BioBERT NER ×3 / BERT-base | < 2GB | CPU로도 가능 |
| dense baseline | gtr-t5-large | ≈ 1.5GB | |

**권장: 48GB 1장 (A6000 / L40S) 또는 A100 40GB.** 논문의 기존 실험도 A6000에서 수행되었습니다(Fig. 3 캡션).

- **24GB (3090 / 4090 / L4)**: AutoAIS가 bf16으로 빠듯하게 들어갑니다. ALCE `utils.py`의 `get_max_memory()`에서
  `free_in_GB-6`을 `free_in_GB-2` 정도로 완화해야 합니다. 13B 생성은 불가.
- **16GB 이하**: 8-bit(≈11GB) / 4-bit(≈6GB) 양자화로 실행은 가능하나, **논문의 기존 수치와 직접 비교할 수 없습니다.**
  방향 탐색용으로만 쓰고 최종 표에는 넣지 마십시오.

**디스크**: AutoAIS 체크포인트만 **45.5GB**(fp32 5샤드). gtr-t5-xxl 19GB, NER 1.5GB.
생성 모델까지 받으면 총 **160GB+**. 최소 **70GB 여유** 필요.

**예상 소요**: ASQA 948건 기준 설정 하나당 NLI 호출 약 7,000회.
A6000 bf16에서 설정당 30–60분, 6개 방법 × 2개 데이터셋 = **6–12시간** 규모로 예상합니다(추정치).

## 3. 실행 순서

```bash
# 0) 환경
conda create -n llmcite python=3.11 -y && conda activate llmcite
pip install -r requirements.txt
pip install torch transformers sentence-transformers accelerate   # GPU 추가분
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt'); nltk.download('punkt_tab')"

# 1) ALCE 데이터 (이미 받았다면 생략)
git clone https://github.com/princeton-nlp/ALCE.git ~/ALCE && cd ~/ALCE && bash download_data.sh

# 2) 동작 확인 (모델 소량 로드)
python extract_keywords.py --self-check

# 3) keyword 캐시 생성 — 제안 방법 및 E4/E5 ablation
python extract_keywords.py --dataset asqa    --extractor general              # 기본
python extract_keywords.py --dataset asqa    --extractor general --no-stem    # E4
python extract_keywords.py --dataset asqa    --extractor domain               # E5
python extract_keywords.py --dataset qampari --extractor general

# 4) 인용 파일 생성 (CPU)
python run_experiments.py --build \
    --methods full_token_jaccard,citefix_intersection,citefix_ksc,tfidf,bm25
python run_experiments.py --build --datasets asqa --methods keyword_jaccard \
    --keyword-cache cache/asqa-general-stem-top5.pkl

# 5) 채점 (대형 GPU)
python run_experiments.py --eval --alce ~/ALCE

# 6) 효율성 재측정 (E10 / E11)
python measure_efficiency.py --dataset asqa --limit 200
```

`--alce` 경로는 기본값이 `~/Desktop/gsds/Research/ALCE`이므로 서버에서는 반드시 지정하십시오.

## 4. 서버에서 먼저 확인할 것

1. `python extract_keywords.py --self-check` — NER 파이프라인이 로드되고 키워드가 뽑히는지
2. `nvidia-smi` 여유 VRAM이 28GB 이상인지 (아니면 `get_max_memory()` 수정)
3. `df -h` 여유 디스크 70GB 이상인지
4. `run_experiments.py --eval --dry-run` 으로 명령만 먼저 출력해 경로 확인

## 5. 남은 설계 결정

- **`--field` 선택**: 현재 기본값은 `answer`(ALCE gold 장문 답변)입니다. 생성기 변동성을 제거해
  인용 방법만 비교하는 설정이라 깔끔하지만, 논문의 기존 프로토콜은 생성된 답변을 씁니다.
  기존 Table 1·4와 같은 축에서 비교하려면 생성 답변(`--field output`)이 필요하고, 그러면 생성 단계도 서버에서 돌려야 합니다.
- **temperature / threshold sweep**: 방법별 최적값을 dev subset에서 정한 뒤 본 실행에 적용해야 합니다
  (`--temperature`, `--threshold`). 현재 기본값은 원본 코드의 값일 뿐 공정한 비교값이 아닙니다.

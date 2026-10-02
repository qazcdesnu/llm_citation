# Rebuttal 진행 요약 01 — 실험 단계 완료 (2026-09-30)

`rebuttal_plan.md`의 마일스톤 순서대로 지금까지 한 일을 정리한 문서다.
세부 근거, 실행 로그, 표 원본은 `rebuttal_plan.md`와 `rebuttal/results/`에 있다.

> **한 줄 요약**: 리뷰어가 요구한 비교 실험(최소 범위)은 모두 끝났다. 결과는 논문의 핵심 주장("keyword 매칭이 dense 임베딩보다 정확하다")을 지지하지 않으며, 논문 Table 1의 baseline이 본문 설명(dense post-hoc)과 달리 ALCE VANILLA 수치라는 점도 확인됐다. 다음 단계는 **논문 주장의 재서술 방향을 공저자·지도교수와 합의**하는 것이다.

## 진행 현황

| 단계 | 내용 | 상태 |
| --- | --- | --- |
| M0 | 진단 및 범위 확정 | ✅ |
| M1 | 평가 하네스 정비 · 서버 환경 | ✅ |
| M2 | E1–E3 (full-token Jaccard, CiteFix) | ✅ — **E1 게이트: 주장 미지지** |
| M3 | 신규 baseline E7–E9 (TF-IDF, BM25, SPLADE) | ✅ |
| M4 | 효율성 재측정 E10 | ✅ |
| M5 | 본문 수정 | ⬜ 재서술 방향 합의 대기 |
| M6 | Rebuttal letter | ⬜ M5 이후 |

범위는 **rebuttal 최소 조건**이다(2026-09-29 결정): 생성 모델 1개(Llama2-7B Chat), ASQA·QAMPARI 각 100건, 리뷰어가 요구한 비교만 수행. 생성 모델 확장, E4–E6, E11, CovidDialog 비교는 제외했다(사유는 `rebuttal_plan.md` "범위 제외" 표).

---

## M0 — 진단 및 범위 확정

- 리뷰 5개 Point를 실험 11개(E1–E11)로 나누고 의존성 순서로 배열.
- **CiteFix 정독**: CiteFix의 "keyword matching"은 keyword 추출이 아니라 **전체 토큰 교집합**이다. 따라서 Point 2(full-token Jaccard)와 Point 5(CiteFix 비교)는 사실상 같은 실험이다. CiteFix는 코드·데이터 비공개라 우리 데이터에 §3.1/§3.2를 재구현.
- **Fig. 6 결함 발견**: 공개 코드(`processing_time.ipynb`)에서 제안 방법만 미리 계산된 keyword를 읽고 시간을 쟀다. keyword 추출(BERT/BioBERT) 비용이 빠져 있다 → Point 4를 "문구 수정"에서 "재측정 필요"로 격상.

## M1 — 평가 하네스 정비 · 서버 환경

**하네스 (로컬에서 작성)**
- 모든 방법이 하나의 점수 함수 인터페이스와 같은 배정 규칙을 쓰도록 `rebuttal/baselines.py` 구축. 원래 코드는 방법마다 temperature·threshold가 달라 비교가 불공정했다.
- ALCE `eval.py`(T5-XXL NLI 기반 AutoAIS)로 채점하도록 `alce_adapter.py`, `run_experiments.py` 작성. 자체 지표를 만들지 않고 논문과 같은 프로토콜 사용.

**서버(GSDS) 이전**
- Slurm GPU 사용 유의사항 정리: `about-server/slurm-gpu-guide.md`.
- 24GB GPU(RTX 3090/4090)만 있어 T5-XXL 채점을 **GPU 2장**에 나눠 올리도록 설정. ALCE 코드 수정 없이 동작함을 확인.
- 노트북 경로 하드코딩 제거(`ALCE_DIR`), 작업 디렉토리 `/shared/s3/lab03/jinwoongkim`(홈 quota 100GB 회피).
- conda 환경 `llmcite` 구축(`rebuttal/setup/setup_env.sbatch`). **transformers<5로 고정** — ALCE가 transformers 5에서 제거된 인자를 써서, ALCE 원본을 고치지 않기 위해 라이브러리를 낮춤.
- 생성 → 재인용 → GPU 2장 채점 전체 경로를 점검 스크립트로 검증(`rebuttal/setup/m1_smoke.sbatch`).

**조사로 확정한 사실**
- **채점 대상은 LLM 생성 답변**. Table 1이 생성 답변 기준이고, 리뷰어도 "문장을 생성한 후 비교"를 전제했다.
- **논문의 "MedDialog" 61건은 실제로 CovidDialog-English test split**이다. 61건 모두 CovidDialog 원문과 일치. 논문 인용 정정 필요(M5).
- 공저자 폴더(`/shared/s3/lab03/juhyeonkim/ALCE/`)에서 CovidDialog 원본 생성 결과, 사람 평가 자료, ASQA 결과 등 원본 자료 확보. FAISS 벡터 DB는 없음.
- `appendix_data.pkl`(Appendix C.1)은 MedDialog가 아니라 **PubMedQA 200건**(기존 기록 정정).
- PubMed 2023 baseline은 공식 경로에서 사라져 Wayback Machine에서 1,164/1,166 파일 복구(`rebuttal/pubmed/`). 이후 CovidDialog 비교를 범위에서 빼면서 현재는 보관만 함.
- GPT(OpenAI API)는 CovidDialog 평가에만 필요 → 범위 제외로 현재 불필요.

## M2 · M3 — 인용 정확도 비교 (E1–E3, E7–E9)

**설정**: Llama2-7B Chat이 ALCE VANILLA 프롬프트로 생성한 답변(ASQA·QAMPARI 각 100건, `quick_test 100`, seed 42). 생성기가 붙인 인용을 지우고, 모든 방법이 **같은 답변 · 같은 5개 문서 · threshold 0**으로 다시 인용. 모든 방법이 문장마다 인용을 하나씩 붙이므로 재현율 = 정밀도 = F1.

| 방법 | ASQA | QAMPARI |
| --- | ---: | ---: |
| **E9 SPLADE** | **60.8** | **17.7** |
| Dense MIPS (gtr-t5-xxl), post-hoc | 56.3 | 14.0 |
| E1 full-token Jaccard | 56.1 | 10.2 |
| E2 CiteFix §3.1 | 55.3 | 12.7 |
| E3 CiteFix §3.2 KSC | 55.1 | 12.9 |
| **Keyword Jaccard (제안 방법)** | **53.3** | **10.8** |
| E7 TF-IDF | 52.3 | 13.8 |
| 제안 방법 (threshold 0.2, 논문 설정) | 51.8 | 10.8 |
| E8 BM25 | 48.6 | 13.3 |
| (참고) VANILLA: 생성기가 직접 붙인 인용 | F1 52.8 | F1 10.8 |

- 우리 dense 구현이 ALCE 공식 `post_hoc_cite.py`와 **두 데이터셋 모두 정확히 일치**(56.3 / 14.0) → 비교 경로 검증.
- **E1 게이트: 지지되지 않음.** 제안 방법은 ASQA에서 full-token Jaccard보다 낮고(53.3 < 56.1), QAMPARI에서는 비슷하다(10.8 vs 10.2). dense post-hoc보다는 두 데이터셋 모두 낮다.
- 제안 방법은 9개 중 ASQA 6위, QAMPARI 7위. SPLADE가 두 데이터셋 모두 1위.
- 주의: 생성 모델 1개 · 100건이고, ALCE가 보고한 같은 모델의 seed 간 표준편차가 ±4.5라서 2–3점 차이는 확정적이지 않다.

**논문 Table 1 baseline의 정체 (확인)**
- ALCE 논문(arXiv:2305.14627) 부록 Table 19·20의 **VANILLA** 인용 수치가 논문 Table 1 baseline과 **5개 모델 × 2개 데이터셋, 10쌍 모두 정확히 일치**한다.
- 본문 §5.2의 "gtr-t5-xxl post-hoc MIPS" 설명과 다르다. 또한 baseline은 전체 dev set · 3 seeds 평균이고 제안 방법은 100건이라 샘플도 다르다.
- 즉 논문의 개선은 "생성기 자체 인용 대비 post-hoc 재인용"의 효과이며, "keyword 방식이 dense보다 정확하다"는 근거가 되지 못한다.

**수정한 버그**: ① QAMPARI 출력이 쉼표 없이 이어져 `eval.py`의 답변 분할이 깨짐. ② ASQA 인용 표시가 마침표 뒤에 붙어 다음 문장의 인용으로 채점됨. 둘 다 수정하고 재채점했다.

## M4 — 효율성 재측정 (E10)

**설정**: Fig. 6과 같은 PubMedQA 200건(969문장). 각 방법을 원문에서 점수 행렬까지 측정하되 특징 추출을 측정 구간에 포함. 신경망은 모두 배치 32, 3회 중앙값, RTX 3090.

| 방법 | 추론 시간 (200건) | 추론 GPU 메모리 |
| --- | ---: | ---: |
| 제안 방법, Fig. 6 방식 (keyword 미리 계산) | 0.003초 | – |
| **제안 방법 + 추출 (general, BERT 1개)** | **7.7초** | 247MB |
| **제안 방법 + 추출 (domain, BioBERT 3개)** | **23.6초** | 673MB |
| TF-IDF / BM25 (CPU) | 0.41초 / 0.34초 | – |
| E1 full-token (CPU) | 1.0초 | – |
| **dense gtr-t5-xxl** | **175.1초** | 19,851MB |
| dense gtr-t5-large | 14.7초 | 1,438MB |
| SPLADE | 5.6초 | 603MB |

- **Fig. 6 결함 확인**: 추출을 넣으면 0.003초 → 7.7–23.6초. TF-IDF·BM25보다 19–70배 느리다(TF-IDF 대비 19–57배, BM25 대비 23–70배).
- **gtr-t5-xxl 대비 우위는 유지**: 7.4–22.7배 빠르고, GPU 메모리 29–80배 적다(논문 Fig. 3 주장: 20.6배, 17.9배).
- **SPLADE보다는 효율도 앞서지 않는다.** SPLADE는 정확도도 1위였다.

---

## 리뷰 Point별 현재 대응 상태

| Point | 리뷰어 요구 | 수행한 것 | 결과와 대응 방향 |
| --- | --- | --- | --- |
| 1 | BM25·TF-IDF·SPLADE 비교 | E7·E8·E9 | 수행 완료. SPLADE > 제안 방법, TF-IDF·BM25와는 비슷한 수준 |
| 2 | full-token Jaccard 비교 | E1 | 수행 완료. keyword 선택의 이득이 확인되지 않음 → 주장 재서술 필요 |
| 3 | 단계별 ablation | E1이 핵심 ablation을 겸함 | E4·E6은 범위 제외. threshold는 기존 Appendix C.3으로 대응, E5는 Limitations로 대응 |
| 4 | "no neural inference" 표현 | E10 재측정 | 문구를 "유사도 계산 단계"로 한정, Fig. 6 수치 교체. 효율성 주장은 dense MIPS 대비로 한정 |
| 5 | CiteFix 비교 | E2·E3 | 수행 완료. CiteFix §3.1 ≈ full-token 계열로 제안 방법보다 약간 높음 |

## 다음 단계 (M5 · M6)

**결정이 필요한 것**
1. **재서술 방향** — 가장 중요. 현재 결과로 유지 가능한 주장과 어려운 주장:

   | 주장 | 판단 |
   | --- | --- |
   | 생성기 자체 인용(VANILLA)보다 낫거나 비슷하다 | 유지 가능 |
   | 단어 기반 post-hoc 방법들과 비슷한 정확도 | 유지 가능 |
   | dense MIPS(gtr-t5-xxl)보다 훨씬 가볍고 빠르다 | 유지 가능 (E10) |
   | 인용 근거를 해석할 수 있다 | 유지 가능 |
   | 의료 대화(CovidDialog)에서 우세 | 기존 결과로 유지 가능. 단 그 baseline encoder 확인 필요 |
   | dense 임베딩보다 정확하다 | ❌ |
   | keyword 선택이 성능을 만든다 (Point 2) | ❌ |
   | TF-IDF·BM25·SPLADE보다 효율적이다 | ❌ |

2. **SPLADE 결과를 어떻게 다룰지** — 정확도와 속도 모두 제안 방법보다 앞선다. 논문 §6 Future work가 이미 SPLADE식 확장을 언급하므로 한계·향후 방향으로 연결하는 방안이 있다.
3. **§5.2 baseline 서술 정정** — 결과와 무관하게 필요한 사실 정정. 원 실험을 한 공저자의 경위 확인이 필요하다.

**남은 공저자 확인 사항**: `asqa_comp.pkl`의 `ours_*` 컬럼 의미, CovidDialog GPT-4 점수가 어느 컬럼(`jaccard_output` / `kw_jaccard_output`)으로 나왔는지, CovidDialog baseline encoder.

**M5 본문 수정 항목** (`rebuttal_plan.md` M5): §2 "no neural inference" 문구, Fig. 3·6 캡션, CiteFix related work 추가, 비교표 삽입, "ablation study" 용어 정정, **"MedDialog" → CovidDialog-English 정정**, **§5.2 baseline 정정**, **주장 범위 재서술**.

---

## 참고: 파일 위치

| 무엇 | 위치 |
| --- | --- |
| 전체 계획 · 근거 · 로그 | `rebuttal_plan.md` |
| 인용 정확도 표 | `rebuttal/results/m2_scores.md` |
| 효율성 표 · 원자료 | `rebuttal/results/e10_efficiency.md`, `e10_efficiency.json` |
| 실험 실행 스크립트 | `rebuttal/experiments/m2.sbatch`, `m3_splade.sbatch`, `e10.sbatch` |
| 환경 설치 · 점검 | `rebuttal/setup/`, `rebuttal/SERVER.md`, `about-server/slurm-gpu-guide.md` |
| 생성 답변 · 인용 파일 · 채점 결과 (서버) | `/shared/s3/lab03/jinwoongkim/ALCE/result/`, `/shared/s3/lab03/jinwoongkim/runs/` |

**주요 커밋**: `d9c2b81`·`e8b1393` (M1 서버 환경), `29cfc43` (M2), `afcf1a4` (M3 SPLADE), `b83d8be` (E10)

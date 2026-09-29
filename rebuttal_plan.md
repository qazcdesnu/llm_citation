# Rebuttal 진행 계획

> **현재 상태** (2026-09-28) — M0 완료, M1 서버 이전 중
>
> | 단계 | 내용 | 상태 |
> | --- | --- | --- |
> | M0 | 진단 및 범위 확정 | ✅ 완료 |
> | M1 | 평가 하네스 정비 | 🔄 서버(GSDS) 이전 중 — 경로 수정 완료, 환경·ALCE 설치 및 생성 답변 입력 코드 남음 |
> | M2 | 저비용 실험 (E1–E6) | ⬜ 대기 — E1–E3은 **1단계**, E4–E6은 **2단계** |
> | M3 | 신규 baseline (E7–E9) | ⬜ 대기 — 전부 **1단계** (E9 SPLADE 신규 구현) |
> | M4 | 효율성 재측정 (E10–E11) | ⬜ 대기 — **2단계**, 제출 전 필수 |
> | M5 | 본문 수정 | ⬜ 대기 — Point 4 문구는 **1단계** |
> | M6 | Rebuttal letter | ⬜ 대기 |
>
> **실행 환경**: GSDS 서버(RTX 3090/4090 24GB). AutoAIS(T5-XXL 11B)는 GPU 2장으로 ALCE 코드 수정 없이 채점 가능 (`rebuttal/SERVER.md`).
> 작업 디렉토리 `/shared/s3/lab03/jinwoongkim`. **공저자 원본 결과 확보**(`/shared/s3/lab03/juhyeonkim/ALCE/`, 아래 "공저자 원본 자료" 참조) — MedDialog Llama2 Chat 결과가 있어 벡터 DB 없이 재인용 가능.
> PubMed 2023 baseline 다운로드는 MedDialog를 다른 모델로 확장할 때만 필요 (job 492514, `rebuttal/pubmed/`).
>
> **남은 블로커**: ① Llama-2 접근 승인 HF 토큰 ② OpenAI API 키(MedDialog GPT-4 평가, 2단계) ③ 공저자 확인 — **CovidDialog GPT-4 점수가 어느 컬럼(`jaccard_output` vs `kw_jaccard_output`)으로 나왔는지**, FAISS DB 위치(공저자 폴더엔 없음), "year_partial" 의미, MedDialog baseline encoder, `asqa_comp.pkl`의 `ours_*` 컬럼 의미

`review.md`의 Point 1–5를 의존성 순서로 재배열한 실행 계획.
상태 표기: `[ ]` 미착수 · `[x]` 완료 · `[~]` 진행 중 · 🅰 1단계 · 🅱 2단계

## 실행 우선순위 (2026-09-28 확정)

범위를 "리뷰어가 명시적으로 요구한 비교"(1단계)와 "보강"(2단계)으로 나눈다.
SPLADE · full-token Jaccard · CiteFix만으로 줄이는 안을 검토했으나, 리뷰 원문이 **"BM25로만 또는 TF-IDF로만"을 명시**했고
두 방법은 이미 구현되어 있어 추가 비용이 채점 몇 분뿐이므로 1단계에 포함한다.

### 🅰 1단계 — 리뷰어 요구에 직접 답하는 비교 (필수)

- **데이터**: ASQA · QAMPARI, **LLM 생성 답변**(`--field output`), 논문과 같은 100건(ALCE `run.py --quick_test 100`, seed 42)
- **생성 모델**: Llama2-7B Chat(사람 평가 모델)으로 전 과정을 먼저 완주 → Table 1의 5개 모델로 확장
- **방법** (모두 같은 생성 답변 위에서 재실행)

| 구분 | 방법 | 구현 |
| --- | --- | --- |
| 기준점 | dense baseline (gtr-t5-xxl MIPS), 제안 방법 | 재실행 |
| Point 2 | **E1** full-token Jaccard | ✅ |
| Point 5 | **E2** CiteFix §3.1 · **E3** CiteFix §3.2 KSC | ✅ (E3의 retrieval score가 ALCE `docs`에 있는지 확인) |
| Point 1 | **E9** SPLADE | ❌ 신규 구현 |
| Point 1 | **E7** TF-IDF · **E8** BM25 | ✅ (E7은 ALCE `post_hoc_cite.py --retriever tfidf`도 가능) |

- **비실험**: Point 4 문구 수정 ("requires no neural inference" → 유사도 계산 단계로 한정)
- **게이트**: E1 결과가 나오면 멈추고 검토. full-token Jaccard ≈ 제안 방법이면 기여 서술을 재검토한 뒤 2단계 진입

### 🅱 2단계 — 보강 (1단계 결과 확인 후)

- **E10 · E11** 효율성 재측정 — keyword 추출 포함, SPLADE 포함. PubMedQA 200건(`appendix_data.pkl`). **Fig. 6 결함 때문에 제출 전 필수**
- **E4** stemming on/off · **E6** threshold / top-*k* — ASQA에서 저비용 단계별 ablation
- **MedDialog 다른 모델로 확장** — Llama2 Chat 외 모델은 원본 결과가 없어 코퍼스 재구축(PubMed 2023 복구분) + 재생성이 필요. 가장 비쌈. 진행 여부는 1단계 결과와 남은 기간으로 결정
- **확장** — 생성 모델 9개 전체, ASQA 948 / QAMPARI 1000 전체 dev set

### 🅰 1단계 추가 후보 — MedDialog (Llama2 Chat, 조건: OpenAI API 키)

공저자 폴더의 원본 결과(`llama2_chat-meddialog-…-kwj-citation.pkl`)에 **생성 답변 61건 + 건당 검색 문서 15개**(PubMed 698 · Medline 217, 본문 포함)가 들어 있다.
post-hoc 인용은 답변과 문서만 있으면 되므로 **벡터 DB 재구축 없이** 같은 답변 위에서 전 방법(dense · 제안 · E1–E3 · E7–E9)과 **E5**(BioBERT NER ↔ general extractor)를 돌릴 수 있다.
Llama2 Chat은 사람 평가(Table 2)에 쓴 모델이라 대표성도 있다. 남는 비용은 GPT-4 쌍대 평가뿐이다.

MedDialog를 끝내 수행하지 못하면 E5가 빠진다. 논문 Limitations가 이미 "extractor 선택에 대한 민감도는 정량화하지 않았다"고 인정하므로 rebuttal에서 이 한계로 답한다.

## 서버 이전 후 확정 사항 (2026-09-28)

논문 전문과 원본 코드를 다시 읽고 확정한 내용.

1. **채점 대상은 생성 답변.** Table 1·4가 9개 LLM의 생성 답변 기준이고, 리뷰어도 "문장을 생성한 후 … 비교"를 전제했다. gold 답변(`--field answer`)은 사람이 쓴 글이라 §3의 전제(LLM이 검색 문서의 keyword를 재사용)를 검증하지 못하므로 보조 결과로만 쓴다.
2. **샘플은 논문과 동일하게.** 논문의 100건은 ALCE `run.py --quick_test 100`(seed 42 무작위 추출)으로 추정. 현재 `--limit`은 앞에서 N건을 자르므로 다름 → 수정 필요.
3. **dense baseline은 직접 재실행.** Table 1 baseline은 "ALCE 보고 수치"를 가져온 것이고, ALCE `post_hoc_cite.py`의 기본 retriever는 논문이 말하는 gtr-t5-xxl이 아니라 **gtr-t5-large**다. 같은 생성 답변에 `--retriever gtr-t5-xxl`로 재실행해 비교 조건을 맞춘다.
4. **`main.py`는 MedDialog 전용.** PubMed/Medline FAISS 검색 → 생성 → pkl. ASQA/QAMPARI에 keyword 인용을 적용한 코드는 저장소에 없다.
5. **MedDialog baseline이 논문 설명과 다를 가능성.** `citation.py`의 gtr 경로는 `H` 미정의로 실행 불가, `run_2.sh`는 `--encoder bert-base-uncased --top_k 6`. 논문은 gtr-t5-xxl · top 15. *원본 결과로 확인: 검색 문서는 건당 15개 → top 15가 맞고 `run_2.sh`의 6은 이후 수정본.* baseline encoder는 원본 `vanilla_output`과 bert-base / gtr-t5-xxl 재계산 결과를 대조해 판별 가능. 재실험은 gtr-t5-xxl로.
6. **MedDialog 코퍼스는 공식 경로로 재현 불가** (Llama2 Chat 외 모델로 확장할 때만 필요). PubMed 2023 baseline은 NCBI FTP에서 삭제, MBR(`mbr.nlm.nih.gov`)은 미해결. Wayback Machine에 1165/1166 파일이 원본 md5 그대로 남아 있어 복구 중이며, 빠진 `pubmed23n0673`은 2026 baseline의 같은 PMID 범위로 대체 (`rebuttal/pubmed/README.md`).
7. **데이터셋 배정.** ASQA·QAMPARI = 1단계 전 비교(객관적 NLI 지표). MedDialog = E5 및 도메인 비교(2단계). ASQA/QAMPARI는 원래 general extractor를 쓰므로 그 위의 E5는 성립하지 않아 제외. PubMedQA 200건 = E10·E11.
8. **논문의 "MedDialog 61건"은 CovidDialog-English다** (2026-09-29 확인). `code/code/Citations/dataset/meddialog-test.json` 61건의 description · 환자 발화 · 의사 발화가 **61/61 모두** CovidDialog-English 원문(`COVID-Dialogue-Dataset-English.txt`, 603건)에 존재. 건수(61 대화 · 122 발화 · 전부 2턴)가 CovidDialog 논문 Table 3의 English **test split**(Train 482 / Val 60 / Test 61)과 일치하고, 61건 중 35건이 COVID 언급. 공저자 폴더의 `meddialog.json`(MedDialog-EN HealthCareMagic 229,674건)과는 겹침 0. 공식 split 파일과의 1:1 대조는 원 저장소(`UCSD-AI4H/COVID-Dialogue`)가 내려가 미실시 — 건수 일치로 test split으로 판단.
9. **GPT(OpenAI API)는 CovidDialog 평가에만 필요** (2026-09-29 확인). ALCE `eval.py`는 OpenAI 호출 없이 로컬 T5-XXL NLI로 채점하고, ASQA/QAMPARI 생성도 공개 모델(HF 토큰만 필요)이다. GPT-4는 `GPT4_evaluation.ipynb`의 CovidDialog 쌍대 평가(`gpt-4-1106-preview`, A/B 익명, 4점 척도)에만 쓰였다. §3 Fig. 4의 GPT-4는 생성 모델이라 재실행 불필요.
   - `gpt-4-1106-preview`의 현재 가용성 확인 필요. 다른 모델로 바꾸면 baseline까지 전부 새 모델로 재채점하고 기존 점수와 섞지 않는다. 비용은 61건 × 방법 약 7개 ≈ 400–500회 호출.
   - GPT 없는 보조 지표로 CovidDialog 인용에도 AutoAIS(NLI) 채점 가능. 단 ALCE citation recall은 미인용 문장을 감점해 chit-chat을 인용하지 않는 제안 방법에 불리하므로 대체가 아닌 보조로만 쓴다.
10. **⚠️ CovidDialog GPT-4 평가의 제안 방법 컬럼이 불명확.** 공개 노트북은 `eval_cite_together(dataset, 'vanilla_output', 'jaccard_output', ...)`로 평가하는데, 현재 `citation.py`에서 `jaccard_output`은 **full-token Jaccard**이고 제안 방법은 `kw_jaccard_output`이다. 공저자의 이전 결과 `jaccard_key.csv`(2024-01-13)에는 `kw_jaccard_output` 컬럼이 없고 그 `jaccard_output`은 chit-chat을 인용하지 않는 등 제안 방법처럼 동작 → 버전에 따라 컬럼 의미가 바뀐 것으로 보이며, 논문 점수는 제안 방법으로 매겼을 가능성이 높다. Point 2와 직결되므로 공저자 확인 필수. 재실험에서는 `kw_jaccard_output`(제안)과 `jaccard_output`(E1)을 명시적으로 구분한다.

## 순서가 중요한 이유

리뷰 번호 순(1→5)으로 진행하면 **실험을 두 번 돌리게 됩니다.** 실제 의존성은 다음과 같습니다.

```
Point 4 (효율성 주장)  ──┐
Point 5 (CiteFix 확인) ──┼──> 실험 목록/측정 프로토콜 확정 ──> Point 2 ──> Point 3 ──> Point 1
                         │     (M0)                            (M2)      (M2)      (M3)
                         └──> 재측정 (M4)
```

- **4번과 5번이 먼저**입니다. 둘 다 계산이 거의 필요 없으면서 *뒤 실험의 설계를 바꿉니다.* CiteFix를 나중에 읽으면 baseline 목록이 바뀌어 M3를 재실행해야 하고, 효율성 측정 프로토콜을 나중에 고치면 모든 신규 baseline의 시간/메모리를 다시 재야 합니다.
- **2번이 3번보다 먼저**입니다. full-token Jaccard는 3번 ablation의 한 조건("keyword set → full tokens")과 동일하고, 이미 구현되어 있습니다(아래 참조). 가장 싼 실험이자 핵심 주장의 직접 통제군이므로 여기서 결과가 나빠지면 이후 계획 전체를 재검토해야 합니다.
- **1번이 마지막**입니다. BM25/SPLADE는 유일하게 신규 구현이 필요하고, M1에서 정비한 공통 인터페이스에 의존합니다.

## 사전 조사에서 확인된 사항

계획을 세우며 코드를 확인한 결과 세 가지가 나왔습니다. 모두 계획에 반영되어 있습니다.

1. **full-token Jaccard는 이미 구현·실행되고 있습니다.** `code/code/Citations/citation.py:82` `causal_jaccard()`가 불용어 제거 + stemming 후 전체 토큰으로 Jaccard를 계산하고, 같은 파일의 main 루프가 이를 `jaccard_output` 컬럼으로 매 실행마다 저장합니다. Point 2는 신규 구현이 아니라 **이미 나오고 있는 결과를 평가해서 표에 넣는 작업**입니다.
2. **다만 현재 비교는 공정하지 않습니다.** `citation.py` main에서 제안 방법은 `softmax(/0.05)` + `threshold=0.2`, full-token Jaccard는 `softmax(/0.7)` + `threshold=0`(기본값)으로 돌고 있습니다. 하이퍼파라미터가 한쪽에만 튜닝된 상태라 이대로 보고하면 리뷰어가 바로 지적합니다. M1에서 먼저 맞춰야 합니다.
3. **Appendix C.1의 속도 비교가 keyword 추출 비용을 제외하고 있습니다.** `processing_time.ipynb` cell 8의 `process_rows()`를 보면, Jaccard 분기는 `row['keyword_sentences']` / `row['keyword_documents']`라는 **미리 계산된 컬럼**을 읽는 반면 TF-IDF·LCS 분기는 원문에서 즉석 계산합니다. 즉 Jaccard 0.045초에는 BERT/BioBERT 추론 시간이 들어있지 않습니다. 이것이 정확히 리뷰어가 4번에서 지적한 지점이며, 공개된 코드에 드러나 있습니다.

> **Point 4의 라벨은 `본문 수정`에서 `실험 수행`으로 올려야 할 가능성이 높습니다.** 위 3번 때문에 문구 수정만으로는 방어되지 않고 재측정이 필요합니다. Fig. 3(모델 로드/추론 시간·GPU 메모리)의 측정 스크립트는 저장소에 아예 없어(`grep` 결과 타이밍 코드는 `processing_time.ipynb`가 유일) 포함 여부를 코드로 확인할 수 없습니다. M0-2에서 먼저 확정하세요.

---

## 공저자 원본 자료 (2026-09-28 확인)

`/shared/s3/lab03/juhyeonkim/ALCE/` (2023-12 ~ 2024-01 작업 공간, 공저자 허락하에 읽기 전용으로 확인).

| 파일 | 내용 | 논문과의 관계 |
| --- | --- | --- |
| `llama2_chat-meddialog-singleturn-vanilla-no_entity-kwj-citation.pkl` | MedDialog 61건, Llama2 Chat 생성 답변 + 검색 문서 15개/건 + 인용 방식 9종 컬럼(`vanilla`·`jaccard`·`kw_jaccard`·`causal`·`ensemble_*`) | **Table 1·2 MedDialog(Llama2 Chat)의 원본 결과.** 입력이 `meddialog-test.json` 60/60 고유 대화와 일치 |
| `jaccard_key.csv`, `Daniel_1.csv`, `Jeongsu_1.csv`, `Human Evaluation Ver.ipynb` | 위 결과의 csv, 사람 평가 시트 | Table 2 사람 평가 자료 |
| `asqa_comp.pkl` | ASQA 948건(전체 dev), `vanilla_output`(ALCE 방식 `Document [n]` 인용) · `ours_threshold` · `ours_all` | ASQA 원본 결과로 추정. `ours_*` 텍스트가 생성 답변이 아니라 문서 문장처럼 보여 **의미 확인 필요**. Table 1 baseline이 ALCE post-hoc인지 in-context(VANILLA) 인용인지 판별 근거가 될 수 있음 |
| `llama2-pubmedqa-ner-entity-kwj-citation_ver2.pkl` | PubMedQA 질문 100건, keyword 프롬프트 단일 턴 QA, 문서 15개/건 | 논문 표에 없음. Appendix C.1 200건과 질문 18개만 겹치고 답변은 불일치 → **C.1 데이터와 다른 실행** |
| `mesh_dialogues.json`(260), `combined_data.json`(1260) | PubMed 연구 기반 LLM 작성 다주제 대화 | 논문 결과에 사용 흔적 없음 |
| `pub_*.csv`, `toge_*.csv` | GPT-4 평가 출력 텍스트 | 대응 실험 미확인 |
| FAISS 벡터 DB | — | ❌ 없음 |

**`pubmed_dialog/`(PubMedQA 템플릿 대화, lab06 작성)는 논문 결과에 쓰이지 않았다.** MedDialog 61건과 겹침 0, PubMedQA 실행도 대화 템플릿이 아닌 단일 턴 질문을 입력으로 썼다.

## M0 — 진단 및 범위 확정  ✅ 완료 (2026-09-21)

*새 실험 없음. 이 단계의 결론이 M2–M3의 실험 목록을 확정합니다.*

- [x] Appendix C.1 타이밍 측정 범위 확인 → keyword 추출 제외됨 (`processing_time.ipynb` cell 8)
- [x] full-token Jaccard 기존 구현 여부 확인 → `citation.py:82`에 존재
- [x] **Fig. 3 측정 스크립트 확보 시도** → 저장소에도, 이 머신 전체 검색에서도 없음. 타이밍 코드는 `processing_time.ipynb`가 유일
- [x] Fig. 3 포함 여부 확정 → **코드로 확인 불가**. 단 Fig. 6이 추출 비용을 제외함이 확정되었으므로 재측정은 어느 쪽이든 필요 → **Point 4 = `실험 수행`으로 확정**
- [x] **CiteFix 정독** (arXiv:2504.15629 v2) → 아래 요약
- [x] CiteFix 코드/데이터 공개 여부 확인 → **비공개**. 내부 Amazon RAG 제품 + 사람 SME 감사 평가, 모델명 익명화(Model A/B/C), 자체 MQLA 지표. 코드 저장소 없음
- [x] Point 5 라벨 확정 → **`선행 연구 확인, 실험 수행`** (우리 데이터셋에 재구현하는 방식)
- [x] M2/M3 실험 목록 최종 확정 → 아래 실험 목록

### CiteFix 정독 결과

세 가지가 계획을 바꿉니다.

1. **CiteFix의 "keyword matching"은 keyword 추출이 아니라 full-token intersection입니다.** §3.1은 *f*를 "the size of the intersection between the tokens in x_i and x̂_j"로 정의하고, NER이나 keyword extractor를 전혀 쓰지 않습니다. 정규화 상수를 빼면 우리 `causal_jaccard()`와 같습니다. → **Point 2의 통제 실험과 CiteFix 비교가 동일한 실험입니다.** 그리고 두 방법의 차이가 정확히 우리 논문의 keyword 추출 단계이므로, 이 비교 하나가 논문의 핵심 주장을 직접 검증합니다.
2. **CiteFix가 우리 §2 주장을 뒷받침합니다.** §3.1: "We also tried a TF-IDF type of scoring ... but it did not yield good results. We noticed regular IDF being particularly noisy with domain specific keywords." IDF 가중이 도메인 특화 환경에서 불리하다는 우리 주장에 대한 독립적인 산업계 근거입니다. Point 1 rebuttal에 인용 가능 — 다만 baseline을 직접 돌려야 하는 의무는 그대로입니다.
3. **문자 그대로의 head-to-head는 불가능합니다.** 데이터·코드 비공개이고 평가가 사람 감사 기반입니다. 우리 데이터셋에 §3.1/§3.2를 재구현하고, 그 사유를 rebuttal에 명시하는 것이 유일하게 가능한 대응입니다.

### 확정된 실험 목록

| ID | 실험 | 대응 Point | 단계 |
| --- | --- | --- | --- |
| E1 | full-token Jaccard (`jaccard_output` 평가) | 2, 3 | M2 |
| E2 | CiteFix §3.1 재구현 — 정규화 없는 token intersection | 5 | M2 |
| E3 | CiteFix §3.2 KSC — λ·f_keyword + (1−λ)·r(q,d), λ=0.8 | 5 | M2 |
| E4 | stemming on/off | 3 | M2 |
| E5 | domain NER → general extractor | 3 | M2 |
| E6 | threshold / top-*k* 민감도 | 3 | M2 |
| E7 | TF-IDF citation baseline | 1 | M3 |
| E8 | BM25 citation baseline | 1 | M3 |
| E9 | SPLADE citation baseline | 1 | M3 |
| E10 | Fig. 6 재측정 — keyword 추출 포함 | 4 | M4 |
| E11 | Fig. 3 재측정 — extractor load/inference 포함 | 4 | M4 |

CiteFix의 BERTScore(§3.3) / fine-tuned BERTScore(§3.4) / LLM matching(§3.5) 변형은 제외합니다. 우리 논문의 주장(경량 · 비신경 매칭)과 비교 축이 다르고, §3.4는 자체 학습 데이터 구축이 필요합니다. rebuttal에서 사유를 밝힙니다.

## M1 — 평가 하네스 정비  🔄 진행 중

*모든 baseline이 같은 조건에서 비교되도록 만드는 단계. 여기를 건너뛰면 M2/M3 결과를 신뢰할 수 없습니다.*

- [x] `score_matrix (n_sentences × n_docs) → assign()` 공통 인터페이스 구축 → `rebuttal/baselines.py`
- [x] 제안 방법 · E1 · E2 · E3 · E7 · E8의 점수 함수 구현 및 동작 확인 (CPU)
- [x] **temperature / threshold 공정성 구조 해결** — 하드코딩 제거, 전 방법이 `score_and_assign()` 단일 경로 통과. *실제 sweep은 gold 라벨이 필요하므로 M2에서 수행*
- [x] `causal_jaccard` 명칭 문제 처리 → 신규 코드는 `full_token_jaccard` 사용. 원본 코드는 제출본 보존을 위해 미수정, `rebuttal/README.md`에 기록
- [x] 실행 환경 구축 (`conda env llmcite`) + `rebuttal/requirements.txt`
- [x] 스모크 테스트 — 200건 · 969문장 전량 통과 (`rebuttal/smoke_results.txt`)
- [x] **평가 파이프라인 스크립트화** — ALCE `eval.py` 호출까지 연결 (`run_experiments.py`). 자체 지표를 만들지 않고 논문이 쓴 프로토콜을 그대로 사용
- [x] GPU 실행 코드 작성 — `extract_keywords.py`(E4·E5 스위치 포함), `measure_efficiency.py`(E10·E11)
- [x] 서버 실행 가이드 + 요구 사양 문서화 → `rebuttal/SERVER.md`
- [x] 서버 이전 준비 — 노트북 경로 하드코딩 제거(`ALCE_DIR`), sbatch 내 `source` 기반 conda 활성화, 작업 경로 `/shared/s3/lab03/jinwoongkim` (2026-09-28)
- [ ] 🅰 서버 환경 구축 — `llmcite` 설치(GPU 노드), 드라이버·`torch.cuda` 확인, ALCE clone + 데이터(`$ALCE_DIR`), `eval.py` 의존성
- [ ] 🅰 **생성 답변 입력 경로** — `alce_adapter`가 ALCE `run.py` 결과 JSON(`output`)을 읽도록 확장, 샘플을 `--quick_test 100`·seed 42로 맞춤
- [ ] 🅰 ALCE로 생성 답변 만들기 — Llama2-7B Chat → Table 1의 5개 모델, ASQA·QAMPARI 각 100건
- [ ] 🅰 GPU 경로 검증 — 파일 1개로 AutoAIS 2-GPU 적재·채점 확인 후 전체 제출
- [ ] 🅰 **재실행 결과가 Table 1과 같은 방향인지 확인** — 제안 방법 vs 재실행 dense baseline. 생성 답변을 새로 만들므로 수치 일치가 아니라 방향 일치를 게이트로 둔다

### 스모크 테스트에서 나온 사실

`appendix_data.pkl` (**PubMedQA** 질문 200건 × 문서 4개, 969문장 — Fig. 1·Appendix C.1의 데이터. *2026-09-28 정정: 이전 기록의 "MedDialog"는 오기*)에는 **gold citation 라벨이 없으므로 정확도가 아닙니다.** 아래는 방법 간 *일치율*과 점수 계산 시간입니다.

| 방법 | 점수 계산 시간 | ms/문장 |
| --- | --- | --- |
| keyword_jaccard (제안) | 0.006 s | 0.007 |
| full_token_jaccard (E1) | 1.415 s | 1.461 |
| citefix_intersection (E2) | 0.041 s | 0.042 |
| citefix_ksc (E3) | 0.045 s | 0.047 |
| tfidf (E7) | 0.682 s | 0.704 |
| bm25 (E8) | 0.366 s | 0.378 |

1. **E10 문제가 수치로 재현되었습니다.** 제안 방법이 236× 빠르게 보이지만, 이는 미리 계산된 keyword 집합을 읽기만 하기 때문입니다. 다른 방법들은 원문 토큰화·stemming을 측정 구간 안에서 수행합니다. Fig. 6의 구조적 결함을 우리 실행으로 재확인한 것이며, 재측정 없이는 방어가 불가능함이 분명해졌습니다.
2. **Point 2 축이 유효합니다.** keyword_jaccard와 full_token_jaccard의 인용 할당이 **46.7%만 일치**합니다. 두 방법이 실질적으로 다르게 동작하므로 비교 실험이 의미가 있습니다. 어느 쪽이 더 정확한지는 gold 라벨이 필요합니다(M2).
3. **제안 방법만 이질적입니다.** 어휘 기반 방법들끼리는 0.60–0.75 일치하는데, keyword_jaccard는 전부와 0.40–0.47입니다. keyword 추출이 실제로 다른 신호를 쓰고 있다는 방증입니다.
4. **KSC의 retrieval 항은 거의 영향이 없습니다** (E2와 0.986 일치). 단 `appendix_data.pkl`에 retrieval score가 없어 순위 기반 대체값을 썼으므로 잠정치입니다.

### ALCE 연동 (2026-09-21 추가)

- [x] ALCE 저장소 clone + 데이터 다운로드 (431MB, ASQA 948건 / QAMPARI 1000건)
- [x] `rebuttal/alce_adapter.py` — 우리 점수 함수의 인용 할당을 ALCE `eval.py`가 읽는 결과 JSON 형식으로 변환. 문장 분할을 `eval.py`와 동일하게 맞춤(nltk `sent_tokenize`, QAMPARI는 쉼표 분할)하여 마커가 채점 단위와 정렬되도록 함
- [x] 드라이런 검증 — ASQA·QAMPARI 각 50건 × 5개 방법, 누락 0건, 인용 마커 정상 생성
- [ ] 🅰 본 실행 — 생성 답변 기반으로 확정(2026-09-28), 위 M1 항목 완료 후

**중요: ALCE에는 gold citation 라벨이 없습니다.** `citation_rec` / `citation_prec`는 NLI 모델 `google/t5_xxl_true_nli_mixture`(T5-XXL 11B)로 계산됩니다. 즉 "라벨을 구한다"가 아니라 **11B 모델 추론을 돌린다**가 요구사항입니다.

**부수 소득:** ALCE에 `post_hoc_cite.py --retriever tfidf`가 있습니다. 공식 TF-IDF post-hoc citation 구현이므로, E7은 우리 구현 대신 ALCE 것을 쓰는 편이 리뷰어 설득에 유리합니다. E7 항목에 반영 예정.

### 🚫 M1 잔여 항목 차단 사유

두 항목은 저장소에 없는 자산이 필요합니다.

| 필요한 것 | 용도 | 현재 상태 (2026-09-28) |
| --- | --- | --- |
| ALCE ASQA / QAMPARI 데이터 | recall/precision 계산 | 노트북에만 있음 → 서버 `$ALCE_DIR`에 재설치 필요 |
| `main.py` 실행 결과 pkl (`result/*.pkl`) | MedDialog 원본 생성 결과 | ✅ Llama2 Chat분 공저자 폴더에서 확보. 나머지 모델은 없음 |
| ~~24GB+ VRAM GPU~~ | AutoAIS 채점 | ✅ GSDS 3090 × 2장으로 해결 |
| BioBERT NER · keyword extractor 모델 | E4·E5·E10 | HF에서 다운로드 (`HF_HOME`은 공용 디렉토리) |
| Llama-2 접근 승인 HF 토큰 | 🅰 생성 답변 | 미확인 |
| OpenAI API 키 | 🅱 MedDialog GPT-4 평가 | 미설정 |
| MedDialog 검색 코퍼스 (PubMed 2023) | 🅱 MedDialog 재생성 | Wayback에서 복구 중 (job 492514) |
| GPU 실험 환경 (torch/transformers) | 위 전부 | 서버 `llmcite` 미설치 |

## M2 — 저비용 실험 (기존 파이프라인 재사용) · Point 2, 3, 5

- [ ] 🅰 **E1 full-token Jaccard** — ASQA·QAMPARI 생성 답변 위에서 재실행·채점. **결과가 나오면 게이트 검토** *(Point 2, 3)*
- [ ] 🅰 **E2 CiteFix §3.1 재구현** — 정규화 없는 token intersection *(Point 5)*
- [ ] 🅰 **E3 CiteFix §3.2 KSC 재구현** — λ=0.8, retrieval score 필요(ALCE `docs`에 있는지 확인) *(Point 5)*
- [ ] 🅱 E4 stemming on/off ablation — `stem_entities()` 우회 *(Point 3)*
- [ ] 🅱 E5 domain-specific NER → general extractor 교체 ablation — **MedDialog에서만 성립** (ASQA/QAMPARI는 원래 general extractor) *(Point 3)*
- [ ] 🅱 E6 threshold / top-*k* 민감도 *(Point 3)*
- [ ] 🅱 단계별 성능 하락 폭을 하나의 ablation 표로 정리 (1단계만 끝나면 E1이 핵심 ablation을 겸함)
- [ ] 논문의 기존 "ablation study"(생성 모델 sweep) 명칭 정정 방침 결정

## M3 — 신규 baseline 구현 · Point 1

- [ ] 🅰 E7 TF-IDF citation baseline — 우리 구현 ✅, ALCE `post_hoc_cite.py --retriever tfidf`와 교차 확인
- [ ] 🅰 E8 BM25 citation baseline (`rank_bm25`) — 고정된 retrieved 문서 집합 위에서 문장별 점수화
- [ ] 🅰 **E9 SPLADE citation baseline** — 유일한 신규 구현. 모델 선정 및 sparse 표현 → score_matrix 변환
- [x] ~~CiteFix 재현 여부 결정~~ → M2(E2·E3)로 이동, M0에서 확정
- [ ] 🅰 ASQA·QAMPARI 인용 품질 표 작성 (MedDialog는 🅱) (제안 방법 · dense MIPS · E1–E3 · E7–E9)
- [ ] §2의 "네 가지 차별점" 주장이 수치로 뒷받침되는지 검토 — 안 되는 항목은 주장을 완화

## M4 — 효율성 재측정 · Point 4

- [ ] 🅱 E10 Appendix C.1(Fig. 6) 재측정 — **제출 전 필수** — **keyword 추출 시간 포함**, 모든 방법 동일 조건
- [ ] 🅱 E11 Fig. 3 재측정 — extractor load/inference 및 GPU 메모리 포함 (측정 스크립트 신규 작성 필요)
- [ ] 🅱 M3의 신규 baseline들(SPLADE 포함) 시간/메모리 추가
- [ ] 재측정 후에도 속도 우위가 유지되는지 확인 → 유지되지 않으면 효율성 주장의 강도를 조정

## M5 — 본문 수정

- [ ] 🅰 §2 "requires no neural training or inference" 문구 수정 — 유사도 계산 단계로 한정 *(Point 4)*
- [ ] Fig. 3 / Fig. 6 캡션에 측정 범위 명시 *(Point 4)*
- [ ] 국문 초록 "추가적인 학습 없이도" 표현 점검
- [ ] Related work에 CiteFix 추가 — concurrent work로 위치 명시 + IDF 관련 §3.1 논지를 우리 주장의 방증으로 인용 *(Point 5, 1)*
- [ ] M2 ablation 표 본문 삽입 *(Point 3)*
- [ ] M3 baseline 비교 표 본문 삽입 *(Point 1)*
- [ ] Appendix B "ablation study" → "model sweep" 등으로 용어 정정
- [ ] **"MedDialog" 데이터셋 명칭·인용 정정** — 실제 사용 데이터는 MedDialog(Zeng et al., 2020, [29])가 아니라 **CovidDialog-English**(Ju et al., "On the Generation of Medical Dialogues for COVID-19", arXiv:2005.05442 / ACL 2021 short). §3·§5.1·Table 1·2·4·Fig. 4·Appendix A의 "MedDialog" 표기와 인용 [29]를 교체하거나 "CovidDialog-English (UCSD MedDialog 프로젝트)"로 명시. 결과 수치는 변동 없음. 근거는 아래 "서버 이전 후 확정 사항" 8번
- [ ] 결과가 바뀐 부분에 맞춰 Abstract / Introduction 주장 강도 조정

## M6 — Rebuttal letter 작성

- [ ] Point별 응답 작성 — 각 항목에 수정된 섹션/표/그림 번호를 명시
- [ ] 리뷰어가 요구했으나 수행하지 않은 항목이 있으면 사유 명시
- [ ] 변경 사항 요약(change log) 첨부
- [ ] 최종 검토 후 제출

---

## 리스크

| 리스크 | 영향 | 대응 |
| --- | --- | --- |
| M4 재측정 후 속도 우위가 크게 줄어듦 | 논문의 핵심 셀링포인트인 효율성 주장 약화 | M0-2에서 조기에 확인. 우위가 남는 범위(유사도 계산 단계)로 주장을 재정의 |
| M2에서 full-token Jaccard가 keyword Jaccard와 비슷한 성능 | 논문의 중심 주장(keyword 선택이 기여) 자체가 흔들림 | 가장 먼저 확인해야 하는 이유. 결과에 따라 기여도 재서술 필요 |
| 재실행 결과가 Table 1과 방향이 다름 | 기존 결과의 신뢰성 문제로 번짐 | 새 생성 답변 위 제안 방법 vs 재실행 baseline의 방향 일치를 M1 게이트로 둠. 불일치 시 원인(샘플·생성 설정·baseline encoder)부터 규명 |
| MedDialog 다른 모델 재현 불가(코퍼스·원본 결과 부재) | 도메인 비교가 Llama2 Chat 1개 모델로 한정 | Llama2 Chat 원본 결과로 전 방법·E5 수행(1단계 후보). 확장은 2단계 |
| ~~CiteFix 코드 미공개~~ (M0에서 확정) | 원 데이터 기준 비교 불가 | 우리 데이터셋에 §3.1/§3.2 재구현(E2·E3), rebuttal에 사유 명시 |

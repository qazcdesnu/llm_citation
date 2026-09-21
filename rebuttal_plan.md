# Rebuttal 진행 계획

> **현재 상태** (2026-09-21) — M0 완료, M1 진행 중
>
> | 단계 | 내용 | 상태 |
> | --- | --- | --- |
> | M0 | 진단 및 범위 확정 | ✅ 완료 |
> | M1 | 평가 하네스 정비 | 🔄 코드 완료 · 데이터 차단 |
> | M2 | 저비용 실험 (E1–E6) | ⬜ 대기 |
> | M3 | 신규 baseline (E7–E9) | ⬜ 대기 |
> | M4 | 효율성 재측정 (E10–E11) | ⬜ 대기 |
> | M5 | 본문 수정 | ⬜ 대기 |
> | M6 | Rebuttal letter | ⬜ 대기 |
>
> **블로커**: ALCE gold 라벨 · `main.py` 결과 pkl · NER 모델 · GPU 환경 · OpenAI 키 부재 → M1 잔여 2항목 및 M2 진입 차단 (상세는 M1 절)

`review.md`의 Point 1–5를 의존성 순서로 재배열한 실행 계획.
상태 표기: `[ ]` 미착수 · `[x]` 완료 · `[~]` 진행 중

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
- [ ] 🚫 **recall / precision / GPT-4 eval 파이프라인 스크립트화** — 차단됨 (아래 참조)
- [ ] 🚫 **논문 Table 1·4 기존 수치 재현 확인** — 차단됨 (아래 참조)

### 스모크 테스트에서 나온 사실

`appendix_data.pkl` (MedDialog 200건, 969문장)에는 **gold citation 라벨이 없으므로 정확도가 아닙니다.** 아래는 방법 간 *일치율*과 점수 계산 시간입니다.

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

### 🚫 M1 잔여 항목 차단 사유

두 항목은 저장소에 없는 자산이 필요합니다.

| 필요한 것 | 용도 | 현재 상태 |
| --- | --- | --- |
| ALCE ASQA / QAMPARI 데이터 + gold citation 라벨 | recall/precision 계산 | 저장소에 MedDialog 테스트셋만 존재 |
| `main.py` 실행 결과 pkl (`result/*.pkl`) | 기존 수치 재현의 입력 | 저장소에 없음 |
| BioBERT NER · keyword extractor 모델 | E4·E5·E10 | 미설치 (HF에서 다운로드 가능) |
| OpenAI API 키 | GPT-4 평가 | 미설정 |
| GPU 실험 환경 (torch/transformers) | 위 전부 | `llmcite` 환경은 CPU 전용 |

## M2 — 저비용 실험 (기존 파이프라인 재사용) · Point 2, 3, 5

- [ ] **E1 full-token Jaccard 결과 평가·보고** — `jaccard_output` 컬럼, 3개 데이터셋 × 주요 모델 *(Point 2, 3)*
- [ ] **E2 CiteFix §3.1 재구현** — 정규화 없는 token intersection *(Point 5)*
- [ ] **E3 CiteFix §3.2 KSC 재구현** — λ=0.8, retrieval score 필요 *(Point 5)*
- [ ] E4 stemming on/off ablation — `stem_entities()` 우회 *(Point 3)*
- [ ] E5 domain-specific NER → general extractor 교체 ablation (MedDialog 대상) *(Point 3)*
- [ ] E6 threshold / top-*k* 민감도 *(Point 3)*
- [ ] 단계별 성능 하락 폭을 하나의 ablation 표로 정리
- [ ] 논문의 기존 "ablation study"(생성 모델 sweep) 명칭 정정 방침 결정

## M3 — 신규 baseline 구현 · Point 1

- [ ] E7 TF-IDF citation baseline — `processing_time.ipynb`의 `compute_tfidf_similarity_matrix()` 이식
- [ ] E8 BM25 citation baseline (`rank_bm25`) — 고정된 retrieved 문서 집합 위에서 문장별 점수화
- [ ] E9 SPLADE citation baseline — 모델 선정 및 sparse 표현 → score_matrix 변환
- [x] ~~CiteFix 재현 여부 결정~~ → M2(E2·E3)로 이동, M0에서 확정
- [ ] 전체 방법 × 3개 데이터셋 인용 품질 표 작성 (제안 방법 · dense MIPS · E1–E3 · E7–E9)
- [ ] §2의 "네 가지 차별점" 주장이 수치로 뒷받침되는지 검토 — 안 되는 항목은 주장을 완화

## M4 — 효율성 재측정 · Point 4

- [ ] E10 Appendix C.1(Fig. 6) 재측정 — **keyword 추출 시간 포함**, 모든 방법 동일 조건
- [ ] E11 Fig. 3 재측정 — extractor load/inference 및 GPU 메모리 포함 (측정 스크립트 신규 작성 필요)
- [ ] M3의 신규 baseline들 시간/메모리 추가
- [ ] 재측정 후에도 속도 우위가 유지되는지 확인 → 유지되지 않으면 효율성 주장의 강도를 조정

## M5 — 본문 수정

- [ ] §2 "requires no neural training or inference" 문구 수정 — 유사도 계산 단계로 한정 *(Point 4)*
- [ ] Fig. 3 / Fig. 6 캡션에 측정 범위 명시 *(Point 4)*
- [ ] 국문 초록 "추가적인 학습 없이도" 표현 점검
- [ ] Related work에 CiteFix 추가 — concurrent work로 위치 명시 + IDF 관련 §3.1 논지를 우리 주장의 방증으로 인용 *(Point 5, 1)*
- [ ] M2 ablation 표 본문 삽입 *(Point 3)*
- [ ] M3 baseline 비교 표 본문 삽입 *(Point 1)*
- [ ] Appendix B "ablation study" → "model sweep" 등으로 용어 정정
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
| M1 재현 실패 | 이후 모든 비교 무효 | M1을 M2 진입 게이트로 둠 |
| ~~CiteFix 코드 미공개~~ (M0에서 확정) | 원 데이터 기준 비교 불가 | 우리 데이터셋에 §3.1/§3.2 재구현(E2·E3), rebuttal에 사유 명시 |

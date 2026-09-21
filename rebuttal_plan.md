# Rebuttal 진행 계획

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

## M0 — 진단 및 범위 확정

*새 실험 없음. 이 단계의 결론이 M2–M3의 실험 목록을 확정합니다.*

- [x] Appendix C.1 타이밍 측정 범위 확인 → keyword 추출 제외됨 (`processing_time.ipynb` cell 8)
- [x] full-token Jaccard 기존 구현 여부 확인 → `citation.py:82`에 존재
- [ ] **Fig. 3 측정 스크립트 확보** — 저장소에 없음. 저자 로컬에서 찾거나 재작성 필요
- [ ] Fig. 3이 keyword extractor의 load/inference를 포함했는지 확정 → Point 4 라벨 확정 (`본문 수정` vs `실험 수행`)
- [ ] **CiteFix 정독** (arXiv:2504.15629) — keyword+semantic matching 변형의 구체적 알고리즘 파악
- [ ] CiteFix 코드/데이터 공개 여부 확인 → 재현 가능하면 M3의 baseline으로 편입, 아니면 related work 논의로 한정
- [ ] Point 5 라벨 확정 (`선행 연구 확인` 유지 vs `실험 수행` 추가)
- [ ] 위 결과를 반영해 M2/M3 실험 목록 최종 확정

## M1 — 평가 하네스 정비

*모든 baseline이 같은 조건에서 비교되도록 만드는 단계. 여기를 건너뛰면 M2/M3 결과를 신뢰할 수 없습니다.*

- [ ] `score_matrix (n_sentences × n_docs) → get_text()` 공통 인터페이스로 baseline 플러그인 구조 정리
- [ ] **temperature / threshold 공정성 문제 해결** — 방법별로 동일한 sweep을 돌리고 각자의 최적값에서 비교 (현재: kw=0.05/0.2, jaccard=0.7/0)
- [ ] `causal_jaccard` 함수명 정정 — causal이 아니라 full-token임
- [ ] recall / precision / GPT-4 eval 파이프라인 스크립트화 (수동 노트북 의존 제거)
- [ ] 논문 Table 1·4의 기존 수치 재현 확인 — 재현이 안 되면 이후 비교가 모두 무의미

## M2 — 저비용 실험 (기존 파이프라인 재사용) · Point 2, 3

- [ ] **full-token Jaccard 결과 평가·보고** — `jaccard_output` 컬럼, 3개 데이터셋 × 주요 모델 *(Point 2)*
- [ ] stemming on/off ablation — `stem_entities()` 우회 *(Point 3)*
- [ ] domain-specific NER → general extractor 교체 ablation (MedDialog 대상) *(Point 3)*
- [ ] keyword set → full tokens ablation (= Point 2 결과 재사용) *(Point 3)*
- [ ] threshold / top-*k* 민감도 *(Point 3)*
- [ ] 단계별 성능 하락 폭을 하나의 ablation 표로 정리
- [ ] 논문의 기존 "ablation study"(생성 모델 sweep) 명칭 정정 방침 결정

## M3 — 신규 baseline 구현 · Point 1

- [ ] TF-IDF citation baseline — `processing_time.ipynb`의 `compute_tfidf_similarity_matrix()` 이식
- [ ] BM25 citation baseline (`rank_bm25`) — 고정된 retrieved 문서 집합 위에서 문장별 점수화
- [ ] SPLADE citation baseline — 모델 선정 및 sparse 표현 → score_matrix 변환
- [ ] (M0 결과에 따라) CiteFix keyword+semantic 변형 재현
- [ ] 4개 방법 × 3개 데이터셋 인용 품질 표 작성
- [ ] §2의 "네 가지 차별점" 주장이 수치로 뒷받침되는지 검토 — 안 되는 항목은 주장을 완화

## M4 — 효율성 재측정 · Point 4

- [ ] Appendix C.1(Fig. 6) 재측정 — **keyword 추출 시간 포함**, 모든 방법 동일 조건
- [ ] Fig. 3 재측정 — extractor load/inference 및 GPU 메모리 포함
- [ ] M3의 신규 baseline들 시간/메모리 추가
- [ ] 재측정 후에도 속도 우위가 유지되는지 확인 → 유지되지 않으면 효율성 주장의 강도를 조정

## M5 — 본문 수정

- [ ] §2 "requires no neural training or inference" 문구 수정 — 유사도 계산 단계로 한정 *(Point 4)*
- [ ] Fig. 3 / Fig. 6 캡션에 측정 범위 명시 *(Point 4)*
- [ ] 국문 초록 "추가적인 학습 없이도" 표현 점검
- [ ] Related work에 CiteFix 추가 + concurrent work로 위치 명시 *(Point 5)*
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
| CiteFix 코드 미공개 | 수치 비교 불가 | 논문 보고 수치 인용 + 방법론 차이 논증으로 대체, rebuttal에 사유 명시 |

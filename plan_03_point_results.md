# Rebuttal 진행 요약 03 — 리뷰 Point별 실험 결과와 대응 (2026-10-02, 검토 반영)

리뷰 코멘트를 Point 1–5로 나눈 항목(`review.md`)마다 수행한 실험, 결과, 본문 수정, rebuttal 응답 요지를 정리한 문서다.
재서술 방향은 `plan_02_positioning.md`의 **①+③ 기준**을 따른다.

- **① dense MIPS(gtr-t5-xxl) 대비 훨씬 가볍고, 정확도는 비슷한 수준**
- **③ 인용 근거(겹친 keyword)를 사람이 직접 읽을 수 있음**
- ② 선택적 인용은 A2(CovidDialog 재비교) 결과가 나온 뒤 추가한다. 해당 위치는 `[A2 후 추가]`로 표시했다.

세부 근거와 실행 기록은 `rebuttal_plan.md`, 실험 결과 요약은 `plan_01_summary.md`, 표 원본은 `rebuttal/results/`에 있다.

---

## 0. 공통 실험 설정

**인용 정확도 (Point 1, 2, 3, 5)**
- 데이터: ASQA · QAMPARI 각 100건 (ALCE `run.py --quick_test 100`, seed 42). 논문의 "100건"을 보고 같은 방식이라고 **추정**한 것으로, 논문의 실제 100건 목록과 대조하지는 않았다
- 생성 모델: Llama2-7B Chat 1개 (사람 평가에 쓴 모델), ALCE VANILLA 프롬프트(문서 5개, 2-shot)
- 재인용 방식
  - 생성기가 붙인 인용을 지우고, 모든 방법이 같은 답변 · 같은 5개 문서로 다시 인용
  - 모든 방법이 같은 점수 → 배정 경로(`rebuttal/baselines.py`)를 거침. threshold 0, 즉 문장마다 최고 점수 문서 1개를 인용
  - 그래서 재현율 = 정밀도 = F1
- 채점: ALCE `eval.py --citations` (AutoAIS, T5-XXL NLI). 논문과 같은 프로토콜이며 자체 지표는 쓰지 않음
- 비교 경로 검증: 우리 dense 구현이 ALCE 공식 `post_hoc_cite.py --retriever gtr-t5-xxl`과 두 데이터셋 모두 정확히 일치 (56.3 / 14.0)

**효율성 (Point 4)**
- 데이터: Fig. 6과 같은 PubMedQA 200건 (`appendix_data.pkl`, 969문장)
- 측정 구간: 원문 → (문장 × 문서) 점수 행렬. 특징 추출(keyword 추출, 임베딩 등)을 측정 구간에 포함
- 조건: RTX 3090, 신경망은 모두 배치 32, 워밍업 1회 후 3회 중앙값

**공통 한계 (rebuttal에서 밝힐 것)**
- 생성 모델 1개 · 데이터셋별 100건
- 답변을 새로 생성했으므로(temperature 1.0 샘플링) 새 비교표의 제안 방법 점수는 Table 1과 다르다. **표 안의 비교만 유효하다**
- 차이의 유의성은 아직 검정하지 않았다
  - ALCE가 보고한 Llama2-7B Chat의 seed 간 표준편차는 인용 재현율 기준 **ASQA ±4.5, QAMPARI ±0.9**다. QAMPARI의 2–7점 차이는 이 범위를 넘는다
  - 이 표준편차는 "생성을 다시 하면 점수가 얼마나 흔들리나"이고, 우리 비교는 같은 답변 위에서 인용 방법만 바꾼 짝지은 비교라 맞는 기준이 아니다
  - "비슷하다 / 낮다"를 구분하려면 문항 단위 **paired bootstrap**이 필요하다 (남은 일)

---

## Point 1 — 단어 기반 · sparse baseline 비교 부재

**리뷰어 지적**
- "문장을 생성한 후, BM25로만 또는 TF-IDF로만 비교한다거나, … SPLADE 등과도 비교실험이 포함되어야 합니다."
- 세부 요구
  - BM25 단독 baseline
  - TF-IDF 단독 baseline
  - SPLADE baseline
  - 생성된 문장 기준, 같은 post-hoc 인용 설정에서 비교

**원고의 문제**
- §2에서 BM25 · TF-IDF · SPLADE를 이름까지 들며 차이를 서술하지만, 셋 중 어느 것도 실험하지 않음
- TF-IDF는 Appendix C.1의 처리 시간 비교에만 등장하고 인용 품질 비교는 없음

**수행한 실험**
- E7 TF-IDF — 우리 구현 (ALCE `post_hoc_cite.py --retriever tfidf`와의 교차 확인은 아직 하지 않음. 교차 확인은 dense만 수행)
- E8 BM25 — `rank_bm25`, 고정된 5개 문서 위에서 문장별 점수 계산
- E9 SPLADE — `naver/splade-cocondenser-ensembledistil` (SPLADE++), 신규 구현

**결과 (인용 F1, ASQA / QAMPARI)**
- E9 SPLADE: **60.8 / 17.7** — 두 데이터셋 모두 1위
- Dense MIPS (gtr-t5-xxl): 56.3 / 14.0
- 제안 방법 (keyword Jaccard): **53.3 / 10.8**
- E7 TF-IDF: 52.3 / 13.8
- E8 BM25: 48.6 / 13.3
- 정리
  - ASQA: 제안 방법 > TF-IDF · BM25, 제안 방법 < SPLADE
  - QAMPARI: 제안 방법 < 세 방법 모두
  - 효율성(E10)도 TF-IDF · BM25(CPU 0.3–0.4초)와 SPLADE(5.6초)가 제안 방법(7.7초 이상)보다 빠름

**해석 (①+③ 기준)**
- "단어 기반 · sparse 방법보다 정확하다"는 주장은 할 수 없음
- TF-IDF · BM25와는 비슷한 수준(ASQA 위, QAMPARI 아래)
- SPLADE가 정확도와 속도 모두 앞섬 → 숨기지 않고 보고
- 제안 방법이 내세울 수 있는 것
  - ① 같은 수준의 정확도대에서 dense gtr-t5-xxl보다 훨씬 가벼움 (Point 4)
  - ③ 인용 근거가 "겹친 keyword 집합"으로 바로 드러남
    - dense와는 분명히 다름 (임베딩 내적은 근거를 단어로 보여 주지 못함)
    - BM25 · TF-IDF도 겹친 단어 목록은 보여 줄 수 있으므로, 이들과의 차이는 "근거가 **짧고 의미 있는 개체명 집합**으로 남는다"는 정도로 좁혀 서술

**본문 수정**
- M3 비교표(제안 방법 · dense · E1–E3 · E7–E9)를 §5에 삽입
- §2 "네 가지 차별점" 서술을 수치에 맞춰 완화
  - 정확도 우위로 읽힐 수 있는 표현 삭제
  - 차별점을 "집합 연산 기반이라 근거를 읽을 수 있음"(③)으로 좁힘
- §6 Future work의 "SPLADE식 확장" 언급을 SPLADE 결과와 연결 — keyword 인용에 학습된 sparse 가중치를 접목하는 방향

**Rebuttal 응답 요지**
- 요청한 세 baseline을 모두 같은 생성 답변 · 같은 설정에서 실행해 표로 추가했다
- SPLADE가 가장 높았고, 제안 방법은 TF-IDF · BM25와 비슷한 수준임을 그대로 보고한다
- 이에 따라 기여 서술을 "더 정확한 인용"에서 "dense 대비 가볍고 근거를 해석할 수 있는 인용"으로 조정했다
- SPLADE와의 결합은 향후 방향으로 제시한다

---

## Point 2 — keyword 선택 자체의 기여를 분리하지 않음

**리뷰어 지적**
- "full-token Jaccard … 등과도 비교실험이 포함되어야 합니다."
- 세부 요구
  - 같은 Jaccard 점수 계산에 keyword 추출만 빼고 전체 토큰을 쓰는 대조군
  - 논문의 핵심 주장("keyword 겹침이 출처를 가리킨다")을 최종 과제(인용 정확도)에서 직접 검증

**원고의 문제**
- §3의 근거(keyword 겹침 0.21 vs 일반 명사 0.08 등)는 단어 겹침 비율일 뿐, 인용 정확도 결과가 아님

**수행한 실험**
- E1 full-token Jaccard — 불용어 제거 + stemming 후 전체 토큰으로 Jaccard 계산
  - 원본 코드 `citation.py`의 `causal_jaccard()`와 같은 계산. 신규 코드에서는 `full_token_jaccard`로 이름을 바꿈
  - 원본 코드에서 방법마다 달랐던 temperature · threshold를 하나로 맞춤 (M1)

**결과 (인용 F1, ASQA / QAMPARI)**
- 제안 방법: 53.3 / 10.8
- E1 full-token Jaccard: **56.1 / 10.2**
- ASQA는 full-token이 2.8점 높고, QAMPARI는 제안 방법이 0.6점 높음 → 두 차이 모두 작지만 유의성은 미검정 (0절 "공통 한계")
- 효율성: full-token은 CPU 1.0초, 제안 방법은 keyword 추출 포함 7.7초(general) / 23.6초(domain)
- 참고(스모크 테스트): 두 방법의 인용 배정 일치율 46.7% → 실제로 다르게 동작함

**해석 (①+③ 기준)**
- keyword 선택이 인용 정확도를 높인다는 근거는 없음
- keyword 선택은 속도에서도 이득이 아님 (full-token보다 느림)
- keyword 선택이 남기는 이득은 ③ 해석 가능성
  - full-token은 겹친 단어에 일반 어휘가 섞여 근거가 흐려짐
  - keyword는 질병명 · 약물명 · 개체명처럼 짧고 의미 있는 집합이 인용 이유로 남음 (Fig. 1)
- §3의 겹침 비율 분석은 "LLM이 검색 문서의 keyword를 재사용한다"는 관찰로 유지하되, 정확도 주장의 근거로 쓰지 않음

**본문 수정**
- "keyword 선택이 성능을 만든다"는 서술 삭제 또는 약화 (Abstract · Introduction · §3 · §5.3 · Conclusion)
- E1을 비교표와 ablation(Point 3)에 그대로 보고
- keyword 선택의 역할을 "정확도를 비슷하게 유지하면서 인용 근거를 간결하게 만드는 단계"로 재정의

**Rebuttal 응답 요지**
- 제안한 대조군을 그대로 실행했다
- 위키 기반 QA에서 keyword 선택의 정확도 이득은 확인되지 않았으며(ASQA −2.8, QAMPARI +0.6), 이를 본문에 그대로 보고한다
- 따라서 keyword 선택의 기여를 정확도가 아니라 인용 근거의 해석 가능성으로 다시 서술했다

---

## Point 3 — 단계별 ablation 부재

**리뷰어 지적**
- "ablation study에서 각 단계별 뺐을 때, 제안한 방법들의 성능 하락이 어떻게 되는지 보여줄 필요가 있습니다."
- 세부 요구 (파이프라인 §4: keyword 추출 → stemming → Jaccard 행렬 → 인용 배정)
  - keyword 집합 → 전체 토큰 (E1)
  - stemming 켜기 / 끄기 (E4)
  - 도메인 NER 추출기 → 일반 추출기 (E5)
  - threshold / top-*k* 민감도 (E6)

**원고의 문제**
- Appendix B의 "ablation study"는 생성 모델을 바꿔 본 것(model sweep)이지 파이프라인 단계를 뺀 것이 아님
- Appendix C.1 "Processing time ablation"도 외부 유사도 방법들의 속도 비교임

**수행한 실험**
- E1 (keyword 집합 → 전체 토큰): Point 2 결과를 핵심 ablation으로 제시
- threshold: M2에서 threshold 0과 0.2(논문 설정)를 모두 채점했으므로 이를 ablation 한 축으로 추가
  - ASQA 53.3 → 51.8, QAMPARI 10.8 → 10.8
  - threshold 0.2에서 인용을 생략한 단위: ASQA 127문장 중 3개(2.4%), QAMPARI 528개 답 중 41개(7.8%)
  - 생략된 것은 인용이 필요한 사실 문장 → 위키 QA에서는 생략이 손해
- threshold 구간 안정성: 기존 Appendix C.3 Table 5 (0.15–0.25 사이 결정 93.8% 이상 동일)

**범위에서 뺀 것과 사유**
- E4 stemming on/off
  - 리뷰어가 단계별 ablation을 "또는"으로 제시했고, E1이 핵심 ablation을 겸함
  - 참고: 스위치가 `extract_keywords.py`에 구현되어 있어 추가 비용은 채점 몇 분 수준 → 응답을 보강할 필요가 생기면 가장 먼저 넣을 후보
- E5 도메인 NER → 일반 추출기
  - ASQA · QAMPARI는 원래 일반 추출기를 쓰므로 성립하지 않음. CovidDialog에서만 성립
  - Limitations의 기존 서술("추출기 민감도는 정량화하지 않음")로 답함
- E6 top-*k*
  - top-*k*(인용 후보 문서 수)는 인용 배정에도 영향을 주지만, ALCE 설정(문서 5개)을 고정해 범위에서 뺌
  - threshold 분석으로 민감도 한 축을 대신 제시

**해석 (①+③ 기준)**
- 정확도를 떠받치는 단일 단계는 확인되지 않음. keyword 단계를 빼도(E1) 정확도는 비슷함
- threshold는 위키 QA에서 정확도를 올리지 않음 → 기본 설정의 역할은 ② 선택적 인용과 연결됨 `[A2 후 추가]`

**본문 수정**
- Appendix B "ablation study" → "model sweep"(생성 모델별 결과)으로 용어 정정
- Appendix C.1 "Processing time ablation" → "processing-time comparison"으로 정정
- 진짜 component ablation 표(전체 방법 · E1 · threshold 0 / 0.2)를 본문 또는 부록에 추가

**Rebuttal 응답 요지**
- 기존 "ablation"이 생성 모델 비교였다는 지적을 받아들여 용어를 정정했다
- keyword 단계(E1)와 threshold 단계의 ablation을 추가했다
- 추출기 교체는 의료 데이터에서만 정의되는 비교라 이번 평가 범위 밖이며, Limitations에 명시했다

---

## Point 4 — "requires no neural inference" 표현

**리뷰어 지적**
- "the proposed citation method requires no neural inference"라는 표현은 부적절함 — keyword 추출에 BERT/BioBERT 추론을 쓰기 때문
- 세부 요구
  - 문구 수정 (리뷰어의 직접 요구)
  - 효율성 수치가 추출 비용을 포함하는지 확인 (우리가 추가한 항목)

**원고의 문제**
- §2 네 번째 차별점: "the computation requires no neural training or inference, which yields the efficiency reported in Fig. 3"
- Fig. 6(Appendix C.1)의 Jaccard 시간 0.045초에 keyword 추출이 빠져 있음
  - `processing_time.ipynb` cell 8에서 제안 방법만 미리 계산된 keyword 컬럼을 읽고, TF-IDF 등은 원문부터 계산함
  - 공개 코드로 누구나 확인할 수 있는 결함 → 리뷰어 요구는 문구 수정뿐이지만 재측정을 수행
- Fig. 3은 측정 스크립트가 없어 추출 포함 여부를 코드로 확인할 수 없음

**수행한 실험**
- E10 Fig. 6 재측정 — keyword 추출을 측정 구간에 포함, M3의 신규 baseline(SPLADE 포함)까지 같은 조건으로 측정

**결과 (PubMedQA 200건, 추론 시간 / 추론 시 최대 GPU 메모리)**
- 제안 방법, Fig. 6 방식(keyword 미리 계산): 0.003초
- 제안 방법 + 추출(general, BERT 1개): **7.7초 / 247MB**
- 제안 방법 + 추출(domain, BioBERT 3개): **23.6초 / 673MB**
- dense gtr-t5-xxl: **175.1초 / 19,851MB**
- dense gtr-t5-large (ALCE 기본값): 14.7초 / 1,438MB
- SPLADE: 5.6초 / 603MB
- TF-IDF · BM25 · full-token · CiteFix (CPU): 0.02–1.0초
- 정리
  - gtr-t5-xxl 대비: 추론 **7.4–22.7배 빠름**, GPU 메모리 **29–80배 적음** (논문 Fig. 3 주장: 20.6배, 17.9배)
    - 논문의 추출기 배정(Table 3)에 맞추면: 의료 데이터(domain 추출기) **7.4배 · 29배**, 위키 QA(general 추출기) **22.7배 · 80배**
    - 측정 데이터는 PubMedQA(의료)이므로 이 측정에 해당하는 값은 domain 기준 7.4배다
  - gtr-t5-large 대비: general 추출기는 1.9배 빠르고 메모리 5.8배 적음. domain 추출기는 1.6배 느리고 메모리 2.1배 적음
  - TF-IDF · BM25 대비 19–70배 느림 (TF-IDF 대비 19–57배, BM25 대비 23–70배). SPLADE보다도 느림

**해석 (①+③ 기준)**
- ① "dense gtr-t5-xxl보다 훨씬 가볍다"는 추출 비용을 넣어도 유지됨 → 중심 소구점으로 사용
- 효율성 비교 대상은 gtr-t5-xxl로 한정. 단어 기반 방법과 SPLADE보다 효율적이라고는 주장하지 않음
- 신경망 추론이 필요 없는 것은 유사도 계산 단계뿐이고, 그 단계 덕분에 ③ 근거를 집합으로 읽을 수 있음

**본문 수정**
- §2 문구 수정
  - 변경 전: "the computation requires no neural training or inference"
  - 변경 후(안): 유사도 계산은 신경망 추론 없이 keyword 집합의 교집합 · 합집합만 쓰며, keyword 추출에는 경량 encoder-only 모델(BERT / BioBERT)을 쓴다
- Fig. 6을 추출 포함 수치로 교체 (또는 추출 제외 수치를 두고 캡션에 명시 — 교체를 권장)
- Fig. 3 캡션에 측정 범위 명시 (E11 재측정은 범위에서 뺌)
- 효율성 주장 문장들(Abstract · Introduction · §5)의 비교 대상을 "dense MIPS(gtr-t5-xxl)"로 명시
- 국문 초록 "추가적인 학습 없이도"는 사실이므로 유지 (학습은 하지 않음)

**Rebuttal 응답 요지**
- 지적이 옳다. 문구를 유사도 계산 단계로 한정했다
- 더 나아가 Fig. 6의 측정에 keyword 추출 시간이 빠져 있었음을 확인하고, 추출을 포함해 모든 방법을 다시 측정했다
- 추출을 포함해도 gtr-t5-xxl 대비 7–23배 빠르고 메모리는 29–80배 적다 (의료 데이터용 domain 추출기 7.4배 · 29배, 위키 QA용 general 추출기 22.7배 · 80배)
- 단어 기반 방법과 SPLADE는 더 빠르므로, 효율성 주장의 범위를 dense MIPS 대비로 좁혔다

---

## Point 5 — CiteFix(ACL 2025 Industry) 미논의

**리뷰어 지적**
- "CiteFix: Enhancing RAG Accuracy Through Post-Processing Citation Correction이 있으며, 이 방법과 비교를 할 필요가 있어 보입니다."
- 세부 요구
  - CiteFix를 관련 연구로 논의
  - CiteFix와 직접 비교

**CiteFix 정독 결과 (arXiv:2504.15629 v2)**
- 같은 과제(생성 후 인용 교정)를 다룸
- §3.1 "keyword matching"은 keyword 추출이 아니라 **전체 토큰 교집합 크기** → 정규화를 빼면 우리 E1과 같은 계열
- §3.2 KSC: λ · (토큰 교집합 점수) + (1−λ) · (질의–문서 검색 점수), λ = 0.8
- §3.1에 "TF-IDF식 점수는 도메인 특화 keyword에서 IDF가 noisy해 좋지 않았다"는 서술 → 우리 §2의 IDF 논지와 같은 방향
- 데이터 · 코드 비공개(Amazon 내부 RAG 제품, 사람 감사 평가, 모델명 익명) → 원 논문 조건의 직접 비교는 불가능
- arXiv v1이 2025년 4월 → concurrent work

**수행한 실험**
- E2 CiteFix §3.1 재구현 — 정규화 없는 토큰 교집합
- E3 CiteFix §3.2 KSC 재구현 — λ = 0.8, 검색 점수는 ALCE 문서의 `score` 사용
- §3.3–3.5(BERTScore, fine-tuned BERTScore, LLM 매칭)는 제외
  - 비교 축(경량 · 비신경 매칭)이 다르고, §3.4는 자체 학습 데이터가 필요함

**결과 (인용 F1, ASQA / QAMPARI)**
- E2 CiteFix §3.1: **55.3 / 12.7**
- E3 CiteFix §3.2 KSC: **55.1 / 12.9**
- 제안 방법: 53.3 / 10.8
- 두 CiteFix 변형 모두 제안 방법보다 약간 높음 (ASQA +1.8–2.0, QAMPARI +1.9–2.1)
- 효율성: E2 · E3는 CPU 0.02–0.03초로 제안 방법보다 훨씬 빠름

**해석 (①+③ 기준)**
- CiteFix의 단어 기반 변형은 정확도와 속도 모두에서 제안 방법보다 약간 낫거나 비슷함 → 정확도 · 효율성으로는 차별화할 수 없음
- 제안 방법과 CiteFix §3.1의 차이는 정확히 keyword 추출 단계 → Point 2와 같은 결론
- 차별점은 ③: CiteFix도 겹친 토큰 목록을 근거로 보여 줄 수 있지만 일반 어휘가 섞이고, 제안 방법은 짧고 의미 있는 keyword(개체명) 집합을 근거로 남김
- ② 선택적 인용(겹치는 keyword가 없으면 인용 생략)도 차별점 후보 `[A2 후 추가]`
- IDF 관련 CiteFix 서술은 §2 논지의 방증으로 인용하되, 우리 실험에서 TF-IDF가 QAMPARI에서는 제안 방법보다 높았으므로(13.8 vs 10.8) 과장하지 않음

**본문 수정**
- Related work에 CiteFix 추가
  - concurrent industry work로 위치 명시
  - §3.1이 전체 토큰 교집합이라는 점, 우리와의 차이가 keyword 추출 단계라는 점을 서술
  - IDF 관련 서술을 §2 논지의 독립적 근거로 인용
- E2 · E3를 비교표에 포함
- 원 데이터로 직접 비교하지 못한 사유(비공개 데이터 · 코드)를 각주 또는 본문에 명시

**Rebuttal 응답 요지**
- CiteFix를 정독하고 관련 연구에 concurrent work로 추가했다
- 데이터와 코드가 공개되지 않아 원 조건 비교는 불가능하므로, 우리 방법과 같은 계열인 §3.1 · §3.2를 같은 데이터에 재구현해 비교했다
- 두 변형이 제안 방법과 비슷하거나 약간 높았고, 이는 Point 2와 같은 결론(keyword 추출은 정확도보다 해석 가능성에 기여)이라 그에 맞춰 기여 서술을 조정했다
- BERTScore · LLM 기반 변형은 경량 매칭이라는 우리 논문의 비교 축과 달라 제외했으며, 그 사유를 밝혔다

---

## 리뷰어가 지적하지 않았지만 함께 고치는 것

- **§5.2 baseline 서술 정정**
  - 논문 Table 1 baseline 수치가 ALCE 논문 부록 Table 19 · 20의 **VANILLA**(생성기 자체 인용) 수치와 10쌍 모두 정확히 일치
  - 본문은 "gtr-t5-xxl post-hoc MIPS"라고 서술 → 사실과 다름
  - ALCE 수치는 전체 dev set · 3 seeds 평균이고 제안 방법은 100건이라 샘플도 다름
  - 이번 재실험에서 같은 샘플로 VANILLA와 비교: ASQA F1 53.3 vs 52.8, QAMPARI 10.8 vs 10.8 → 비슷함. 사실로만 진술하고 내세우지 않음
  - 공저자에게 경위 확인 필요
- **데이터셋 명칭 정정**: 논문의 "MedDialog" 61건은 실제로 **CovidDialog-English** test split (61/61 일치). §3 · §5.1 · Table 1 · 2 · 4 · Fig. 4 · Appendix A의 표기와 인용 [29] 교체. 결과 수치는 변동 없음
- **Fig. 6 측정 결함**: Point 4에 포함해 처리 (리뷰어 요구 범위 밖이지만 재측정함)
- 기타: Appendix C.1 Table 5 너비 조정 (`paper edit checklist.md`)

---

## 남은 일

- **A2(CovidDialog 재비교)**: 결과에 따라 `[A2 후 추가]` 위치(Point 3 · 5)와 소구점 ②를 채우거나 제외
- **공저자 확인**
  - Table 1 baseline이 VANILLA였던 경위
  - CovidDialog GPT-4 점수가 어느 컬럼(`jaccard_output` / `kw_jaccard_output`)으로 나왔는지
  - CovidDialog baseline encoder (bert-base인지 gtr-t5-xxl인지)
  - `asqa_comp.pkl`의 `ours_*` 컬럼 의미
- **공저자 · 지도교수 합의**: ①+③ 재서술 방향 (`plan_02_positioning.md` 5절)
- **선택**: E4 stemming on/off — Point 3 응답을 보강하고 싶을 때 저비용으로 추가 가능
- **검토에서 나온 보강 작업** (2026-10-02, 각 30분 안팎)
  - **paired bootstrap**: 같은 답변 위 방법 간 차이의 신뢰구간. 소구점 ①("정확도는 비슷한 수준")을 쓰려면 사실상 필요
  - **E10 keyword 추출기 FP32 재측정**: 논문 Fig. 3은 "모든 모델 FP32"인데 E10에서 추출기만 bf16(원 코드 설정)으로 돌았음
  - (선택) ALCE `post_hoc_cite.py --retriever tfidf`로 E7 교차 확인
- **서버 환경 차이 — 본문 · 부록에 밝힐 것**
  - 새 비교표의 제안 방법 점수(ASQA 53.3)가 Table 1(재현율 56.1 / 정밀도 49.7)과 다른 이유: 답변 재생성(temperature 1.0, torch 시드 미고정)과 threshold 0 조건 → "표 안의 비교만 유효"를 캡션에 명시
  - E10 측정 장비(RTX 3090, AMD EPYC 7502)가 논문 Fig. 3(A6000, Xeon Gold 6342)과 다름 → 절대 시간은 비교하지 않고 배수만 비교한다고 캡션에 명시
  - 부록 재현성 정보: transformers 4.57.6 고정 사유(ALCE 호환), 패키지 목록(`rebuttal/setup/pip-freeze.txt`), AutoAIS를 GPU 2장에 분산 적재(점수 영향 없음 — ALCE 공식 post-hoc 결과와 정확히 일치)
- 다음 단계: 이 문서를 바탕으로 M5(본문 수정) → M6(rebuttal letter)

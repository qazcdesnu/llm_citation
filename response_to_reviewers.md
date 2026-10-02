# 심사의견 답변서 (초안)

> **작성 상태 (2026-10-02)** — 초안이다. 제출 전에 아래 표시를 모두 채우거나 지운다.
> - `[p. ?]`, `[Table ?]`, `[Fig. ?]`: 수정본(M5)의 쪽 · 표 · 그림 번호
> - `[A2 후]`: CovidDialog 재비교 결과에 따라 추가하거나 삭제 (`plan_02_positioning.md` 3.5)
> - `[재측정 후]`: E10 keyword 추출기 FP32 재측정 후 수치 확정
> - `[검정 후]`: paired bootstrap 결과에 따라 "비슷하다 / 낮다" 표현 확정
> - `[공저자 확인]`: 공저자 확인이 필요한 사실관계
> - 재서술 방향(소구점 ①+③)은 공저자 · 지도교수 합의 전이다.
>
> 근거: `plan_03_point_results.md`(Point별 결과), `rebuttal_plan.md`(세부 기록), `rebuttal/results/`(표 원본)

---

논문 제목: LLM 인용 방식의 재고찰: 단순 키워드 매칭의 가능성 탐색 (Rethinking LLM Citations: Exploring the Potential of Simple Keyword Matching)

먼저 논문을 세심하게 검토하고 구체적인 개선 방향을 제시해 주신 심사위원께 감사드립니다.
심사위원께서 지적하신 다섯 가지 사항을 모두 반영하여, 요청하신 비교 실험(BM25, TF-IDF, SPLADE, full-token Jaccard, CiteFix)과 효율성 재측정을 수행하고 그 결과에 맞추어 본문을 수정하였습니다.
특히 추가 실험 결과, 위키 기반 QA에서 제안 방법의 인용 정확도는 일부 기존 방법보다 낮게 나타났습니다. 저희는 이 결과를 그대로 보고하고, 논문의 기여를 "더 정확한 인용"에서 "**dense 임베딩 기반 방법보다 훨씬 가볍고, 인용 근거를 해석할 수 있는 인용**"으로 조정하였습니다.

아래에 각 지적사항에 대한 답변과 수정 위치를 정리하였습니다. 심사위원의 의견은 인용 상자로, 수정된 본문은 별도 문단으로 표시하였습니다.

## 수정 요약

| 지적사항 | 수행한 작업 | 수정 위치 |
| --- | --- | --- |
| 1. 단어 기반 · sparse baseline 비교 부재 | BM25, TF-IDF, SPLADE를 같은 설정에서 실험하고 비교표 추가 | §5 `[Table ?]`, §2, §6 |
| 2. full-token Jaccard 비교 부재 | full-token Jaccard 대조 실험 추가 | §5 `[Table ?]`, Abstract, §1, §3, §5.3, §7 |
| 3. 단계별 ablation 부재 | keyword 단계 · threshold ablation 추가, "ablation" 용어 정정 | §5 또는 부록 `[Table ?]`, Appendix B, C.1 |
| 4. "requires no neural inference" 표현 | 문구 수정, keyword 추출을 포함해 효율성 재측정 | §2, Fig. 3 · 6 `[Fig. ?]`, Abstract, §1 |
| 5. CiteFix 미논의 | 관련 연구에 추가, 같은 데이터에 재구현해 비교 | §2, §5 `[Table ?]` |
| (추가) 저자 자체 점검 | baseline 서술 정정, 데이터셋 명칭 정정 | §5.1, §5.2, Table 1 · 2 · 4, Appendix A |

## 추가 실험의 공통 설정

- **데이터**: ASQA · QAMPARI 각 100건 (ALCE `run.py --quick_test 100`, seed 42).
- **생성 모델**: Llama2-7B Chat (사람 평가에 사용한 모델). ALCE 기본 프롬프트(문서 5개, 2-shot)로 답변을 새로 생성하였습니다.
- **비교 방식**: 생성 모델이 붙인 인용을 제거한 뒤, 모든 방법이 **같은 답변과 같은 5개 문서**에 대해 문장마다 점수가 가장 높은 문서 하나를 인용하도록 하였습니다. 모든 방법이 동일한 점수 계산 · 인용 배정 절차를 거칩니다.
- **평가**: 원고와 동일한 ALCE 평가(TRUE NLI 기반 citation recall / precision)를 사용하였습니다. 모든 문장에 인용이 하나씩 붙으므로 재현율과 정밀도가 같아 F1으로 보고합니다.
- **검증**: 저희가 구현한 dense 방법(gtr-t5-xxl)의 결과가 ALCE 공식 post-hoc 인용 코드의 결과와 두 데이터셋 모두 정확히 일치함을 확인하였습니다.
- **원고 Table 1과의 관계**: 답변을 새로 생성하였기 때문에(temperature 1.0 샘플링), 추가 표의 제안 방법 수치는 Table 1과 다릅니다. **추가 표 안의 비교만 같은 조건**이며, 이를 표 캡션에 명시하였습니다.

**추가 비교 결과** (인용 F1) `[Table ?]`

| 방법 | ASQA | QAMPARI |
| --- | ---: | ---: |
| SPLADE | **60.8** | **17.7** |
| Dense MIPS (gtr-t5-xxl) | 56.3 | 14.0 |
| Full-token Jaccard | 56.1 | 10.2 |
| CiteFix §3.1 (token intersection) | 55.3 | 12.7 |
| CiteFix §3.2 (KSC) | 55.1 | 12.9 |
| **Keyword Jaccard (제안 방법)** | 53.3 | 10.8 |
| TF-IDF | 52.3 | 13.8 |
| BM25 | 48.6 | 13.3 |
| (참고) 생성 모델 자체 인용 | 52.8 | 10.8 |

`[검정 후]` 방법 간 차이에 대한 paired bootstrap 신뢰구간을 표에 함께 보고합니다.

---

## 지적사항 1

> 핵심 주장에 대한 실험들이 여전히 부족합니다. 예를 들어, 문장을 생성한 후, BM25로만 또는 TF-IDF로만 비교한다거나, (…) SPLADE 등과도 비교실험이 포함되어야 합니다.

**답변**

지적에 동의합니다. 원고 §2는 BM25, TF-IDF, SPLADE와의 차이를 서술하면서도 이들을 인용 품질 실험에 포함하지 않았습니다.
요청하신 세 방법을 생성된 답변 기준의 동일한 post-hoc 인용 설정에서 실험하여 비교표 `[Table ?]`에 추가하였습니다.

결과적으로 **SPLADE가 두 데이터셋 모두에서 가장 높은 인용 정확도**를 보였고(ASQA 60.8, QAMPARI 17.7), 제안 방법은 TF-IDF · BM25와 비슷한 수준이었습니다(ASQA에서는 두 방법보다 높고, QAMPARI에서는 낮음).
따라서 "단어 기반 · sparse 방법보다 정확하다"는 해석이 가능한 서술은 삭제하였습니다.

제안 방법의 차별점은 다음 두 가지로 좁혀 서술하였습니다.
- **효율성**: dense 임베딩 기반 방법(gtr-t5-xxl)보다 훨씬 가볍습니다 (지적사항 4 참조).
- **해석 가능성**: 인용 근거가 "문장과 문서에 함께 나타난 keyword(개체명) 집합"으로 바로 드러납니다. dense 방법은 근거를 단어 단위로 보여 줄 수 없고, BM25 · TF-IDF도 겹친 단어를 보여 줄 수는 있으나 일반 어휘가 섞입니다.

SPLADE의 결과는 원고 §6 Future work에서 언급한 "확장 기반 sparse 모델을 keyword 인용에 접목하는 방향"과 연결하여 서술하였습니다.

**수정 사항**
- §5 `[p. ?]`: 추가 비교표 `[Table ?]`와 결과 서술 추가
- §2 `[p. ?]`: 네 가지 차별점 중 정확도 우위로 읽힐 수 있는 표현 삭제, 차별점을 효율성과 해석 가능성으로 한정
- §6 `[p. ?]`: SPLADE 결과와 향후 방향 연결

## 지적사항 2

> (…) full-token Jaccard (…) 등과도 비교실험이 포함되어야 합니다.

**답변**

keyword 추출 단계만 빼고 같은 Jaccard 계산을 전체 토큰(불용어 제거, stemming 적용)에 적용한 대조 실험을 추가하였습니다.

결과는 ASQA에서 full-token Jaccard 56.1, 제안 방법 53.3이고, QAMPARI에서 각각 10.2, 10.8이었습니다. `[검정 후: 차이의 유의성 서술]`
즉 **위키 기반 QA에서 keyword 선택이 인용 정확도를 높인다는 근거는 확인되지 않았습니다.** 이 결과를 본문에 그대로 보고하였습니다.

이에 따라 keyword 선택 단계의 역할을 "정확도를 높이는 단계"가 아니라 "**비슷한 정확도를 유지하면서 인용 근거를 짧고 의미 있는 keyword 집합으로 남기는 단계**"로 다시 서술하였습니다.
§3의 keyword 재사용 비율 분석(keyword 0.21 vs 일반 명사 0.08 등)은 "LLM이 검색 문서의 keyword를 생성문에 재사용한다"는 관찰로 유지하되, 인용 정확도 주장의 근거로는 사용하지 않도록 수정하였습니다.

**수정 사항**
- §5 `[p. ?]`: full-token Jaccard를 비교표와 ablation 표에 추가
- Abstract, §1, §3, §5.3, §7 `[p. ?]`: "keyword 선택이 성능 향상을 가져온다"는 서술 삭제 또는 완화

## 지적사항 3

> 또는 ablation study에서 각 단계별 뺐을 때, 제안한 방법들의 성능 하락이 어떻게 되는지 보여줄 필요가 있습니다.

**답변**

지적하신 대로 원고 Appendix B의 "ablation study"는 생성 모델을 바꾸어 본 실험(model sweep)이었고, Appendix C.1의 "Processing time ablation"도 유사도 방법 간 처리 시간 비교였습니다. 두 용어를 각각 "model sweep", "processing-time comparison"으로 정정하였습니다.

파이프라인 단계별 ablation으로 다음을 추가하였습니다 `[Table ?]`.
- **keyword 추출 단계 제거** (keyword 집합 → 전체 토큰): 지적사항 2의 결과
- **threshold 단계**: 인용 생략 threshold를 0(항상 인용)과 0.2(원고 설정)로 비교하였습니다. ASQA 53.3 → 51.8, QAMPARI 10.8 → 10.8로, 위키 기반 QA에서는 threshold가 정확도를 높이지 않았습니다. threshold 0.2에서 인용이 생략된 경우는 ASQA 2.4%, QAMPARI 7.8%였습니다.
  `[A2 후]` threshold의 역할(인용이 필요 없는 문장의 인용 생략)에 대한 대화 데이터 결과를 추가합니다.
- threshold 구간에 대한 민감도는 기존 Appendix C.3(Table 5)을 함께 참조하도록 하였습니다.

keyword 추출기를 도메인 특화 NER에서 일반 추출기로 바꾸는 비교는, ASQA · QAMPARI가 원래 일반 추출기를 사용하므로 의료 데이터에서만 정의됩니다. 이번 수정에서는 수행하지 못하였으며, Limitations에 이를 명시하였습니다.

**수정 사항**
- Appendix B `[p. ?]`, Appendix C.1 `[p. ?]`: 용어 정정
- §5 또는 부록 `[p. ?]`: 단계별 ablation 표 `[Table ?]` 추가
- §6 Limitations `[p. ?]`: 추출기 교체 비교의 범위 명시

## 지적사항 4

> 일부 표현들, "the proposed citation method requires no neural inference"이라는 것은 적절치 않습니다. 왜냐하면 제안한 방법은 BERT/BioBERT를 돌려서 keyword를 추출하는데, 이 또한 neural inference를 사용하기 때문입니다.

**답변**

지적이 옳습니다. 신경망 추론이 필요 없는 것은 유사도 계산 단계뿐이며, keyword 추출에는 BERT/BioBERT를 사용합니다. 해당 문구를 다음과 같이 수정하였습니다.

> (수정 전) the computation requires no neural training or inference
>
> (수정 후) the similarity computation requires no neural inference — it uses only the intersection and union of keyword sets — while keyword extraction relies on a lightweight encoder-only model (BERT/BioBERT)

또한 효율성 수치가 keyword 추출 비용을 포함하는지 점검한 결과, **Appendix C.1(Fig. 6)의 처리 시간 측정에서 제안 방법만 미리 추출해 둔 keyword를 사용하여 추출 시간이 빠져 있었음**을 확인하였습니다.
이에 Fig. 6과 같은 200개 응답에 대해, 모든 방법의 특징 추출을 측정 구간에 포함하여 다시 측정하였습니다 `[Fig. ?]`.

| 방법 | 추론 시간 (200개 응답) | 최대 GPU 메모리 |
| --- | ---: | ---: |
| 제안 방법 (일반 추출기, BERT 1개) | 7.7초 | 247MB |
| 제안 방법 (도메인 추출기, BioBERT 3개) | 23.6초 | 673MB |
| Dense MIPS (gtr-t5-xxl) | 175.1초 | 19,851MB |
| Dense MIPS (gtr-t5-large) | 14.7초 | 1,438MB |
| SPLADE | 5.6초 | 603MB |
| TF-IDF / BM25 (CPU) | 0.41초 / 0.34초 | – |

`[재측정 후]` 제안 방법의 수치는 keyword 추출기를 FP32로 맞춘 재측정 결과로 교체합니다.

keyword 추출을 포함하더라도 제안 방법은 gtr-t5-xxl보다 추론이 **7.4배(도메인 추출기) – 22.7배(일반 추출기) 빠르고**, GPU 메모리를 **29–80배 적게** 사용합니다.
다만 TF-IDF, BM25, SPLADE보다는 느리므로, 효율성 주장의 비교 대상을 **dense 임베딩 기반 방법(gtr-t5-xxl)으로 한정**하였습니다.

**수정 사항**
- §2 `[p. ?]`: 문구 수정
- Fig. 6 `[p. ?]`: keyword 추출을 포함한 재측정 결과로 교체, 측정 장비 명시
- Fig. 3 캡션 `[p. ?]`: 측정 범위 명시
- Abstract, §1, §5 `[p. ?]`: 효율성 비교 대상을 dense 임베딩 기반 방법으로 명시

## 지적사항 5

> 2025년도 ACL Industry 논문으로 CiteFix: Enhancing RAG Accuracy Through Post-Processing Citation Correction이 있으며, 이 방법과 비교를 할 필요가 있어 보입니다.

**답변**

CiteFix를 검토하여 관련 연구에 추가하였습니다. CiteFix는 생성 후 인용을 교정한다는 점에서 같은 과제를 다루며, 저희 연구와 거의 같은 시기에 공개된 산업계 연구입니다(arXiv 2025년 4월).

CiteFix의 데이터와 코드는 공개되어 있지 않아(사내 RAG 시스템과 사람 감수 평가 기반) 원 논문 조건에서의 직접 비교는 불가능하였습니다.
대신 저희 방법과 같은 계열인 두 변형을 같은 데이터에 재구현하여 비교하였습니다 `[Table ?]`.
- §3.1 keyword matching (전체 토큰 교집합 크기): ASQA 55.3, QAMPARI 12.7
- §3.2 KSC (토큰 교집합 점수 0.8 + 검색 점수 0.2): ASQA 55.1, QAMPARI 12.9

두 변형 모두 제안 방법(53.3 / 10.8)보다 약간 높았습니다.
CiteFix §3.1의 "keyword matching"은 별도의 keyword 추출 없이 전체 토큰을 사용하므로, 제안 방법과의 차이는 정확히 keyword 추출 단계입니다. 따라서 이 결과는 지적사항 2와 같은 결론으로 이어지며, 그에 맞추어 기여 서술을 조정하였습니다.
BERTScore 및 LLM 기반 변형(§3.3–3.5)은 경량 매칭이라는 본 논문의 비교 축과 달라 제외하였고, 그 사유를 본문에 밝혔습니다.

또한 CiteFix가 "도메인 특화 keyword에서는 IDF 가중치가 불안정하다"고 보고한 점은 원고 §2의 논지와 같은 방향이므로 함께 인용하였습니다. 다만 저희 실험에서 TF-IDF가 QAMPARI에서는 제안 방법보다 높았으므로 이를 과장하지 않도록 서술하였습니다.

**수정 사항**
- §2 Related work `[p. ?]`: CiteFix 추가 (동시대 연구로 위치, 제안 방법과의 차이 서술)
- §5 `[p. ?]`: CiteFix 두 변형을 비교표에 포함, 직접 비교하지 못한 사유 명시

---

## 저자 자체 점검에 따른 추가 수정

심사 의견을 반영하는 과정에서 원고의 다음 사항을 추가로 확인하여 수정하였습니다.

**1. Table 1 baseline 서술 정정** `[공저자 확인]`
원고 §5.2는 baseline을 "gtr-t5-xxl을 이용한 post-hoc 인용"으로 설명하였으나, Table 1의 baseline 수치는 ALCE 논문이 보고한 **VANILLA 설정(생성 모델이 답변 생성 중 직접 붙인 인용)**의 수치였습니다.
또한 이 수치는 ALCE의 전체 평가 세트에서 3개 seed를 평균한 값이고, 제안 방법은 100개 샘플에서 평가되었습니다.
§5.2의 서술을 실제 비교 대상에 맞게 정정하고, 평가 샘플의 차이를 명시하였습니다. dense post-hoc 방법과의 같은 조건 비교는 추가 비교표 `[Table ?]`에 제시하였습니다.

**2. 데이터셋 명칭 정정**
원고에서 "MedDialog"로 표기한 61개 대화는 실제로 같은 연구 그룹이 공개한 **CovidDialog-English**의 test split이었습니다.
§3, §5.1, Table 1 · 2 · 4, Fig. 4, Appendix A의 표기와 인용을 정정하였습니다. 실험 결과 수치에는 변동이 없습니다.

**3. 재현성 정보 추가**
추가 실험의 하드웨어(RTX 3090, AMD EPYC 7502)와 소프트웨어 버전을 부록에 명시하였습니다.
효율성 측정 장비가 원고 Fig. 3(A6000, Xeon Gold 6342)과 다르므로, 절대 시간이 아니라 방법 간 배수로 비교하였습니다.

---

다시 한번 논문의 개선에 큰 도움이 된 의견을 주신 심사위원께 감사드립니다.

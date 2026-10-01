# Rebuttal 진행 요약 02 — 소구점과 재서술 방향 (2026-10-01)

M5(본문 수정)에 들어가기 전에, 실험 결과를 바탕으로 논문의 소구점을 다시 정하기 위한 논의 자료다.
실험 결과 자체는 `plan_01_summary.md`, 세부 근거와 실행 기록은 `rebuttal_plan.md`에 있다.

> **권장**: 소구점을 "**가볍고, 해석 가능하고, 필요할 때만 인용하는 post-hoc 인용**"으로 잡는다.
> ① dense MIPS 대비 효율성과 ③ 해석 가능성을 중심에 두고, ② 선택적 인용은 CovidDialog 재비교(A2)로 확인한 뒤 포함 여부를 정한다.
> 위키 기반 QA의 인용 정확도는 SPLADE·dense가 더 높다는 점은 인정하고 한계·향후 방향으로 연결한다.

## 1. 왜 소구점을 다시 정해야 하나

- **논문의 현재 소구점**: "keyword 매칭이 dense 임베딩 기반 post-hoc 인용보다 정확하고 빠르다."
- **실험 결과** (`plan_01_summary.md` M2–M4):
  - 같은 생성 답변 · 같은 조건에서 제안 방법은 dense post-hoc보다 낮다 (ASQA 53.3 vs 56.3, QAMPARI 10.8 vs 14.0). SPLADE가 두 데이터셋 모두 1위(60.8 / 17.7).
  - keyword 선택의 이득이 확인되지 않는다 (E1 full-token: ASQA 56.1 > 53.3).
  - 논문 Table 1의 baseline은 dense post-hoc이 아니라 **ALCE VANILLA**(생성기 자체 인용) 수치다 (10쌍 일치).
  - 효율성: keyword 추출을 포함해도 gtr-t5-xxl보다 7–23배 빠르고 메모리 29–80배 적다. 하지만 SPLADE·TF-IDF·BM25보다는 느리다.
- 리뷰어가 요구한 새 비교표를 내는 순간 위 결과가 드러나므로, 기존 소구점을 그대로 둘 수 없다.

## 2. 소구점 후보

| 후보 | 근거 | 강도 | 비고 |
| --- | --- | --- | --- |
| **① dense MIPS 대비 훨씬 가볍고, 정확도는 비슷한 수준** | E10: gtr-t5-xxl 대비 추론 7.4–22.7배 빠름, GPU 메모리 29–80배 적음. ASQA 정확도 53.3 vs 56.3은 seed 표준편차(±4.5) 안 | 🟢 강함 | QAMPARI 격차(10.8 vs 14.0)는 더 큼. TF-IDF·BM25·SPLADE보다 효율적이라고는 말할 수 없음 |
| **② 인용이 필요 없는 문장에는 인용하지 않음 (선택적 인용)** | CovidDialog 사람 평가 2.88 vs 1.83, GPT-4 평가 2.58 vs 2.09 | 🟡 차별점은 분명, 근거는 기존 실험뿐 | 아래 3절. A2로 확인 필요 |
| **③ 인용 근거를 사람이 읽을 수 있음** | 겹친 keyword(질병명, 약물명 등)가 그대로 인용 이유 (Fig. 1) | 🟡 정성적 | SPLADE도 단어 가중치는 볼 수 있으나, keyword 집합이 더 직관적 |
| ④ 생성기 자체 인용(VANILLA)보다 낫다 | M2: ASQA F1 53.3 vs 52.8, QAMPARI 10.8 vs 10.8 | 🔴 단독으로는 약함 | post-hoc 방법 대부분이 VANILLA보다 높아서 제안 방법만의 장점이 아님. 차이도 표준편차 안. 사실로만 진술 |

## 3. 선택적 인용 상세

### 3.1 동작 원리
논문 설정(`code/code/Citations/citation.py`)은 문장마다 문서별 keyword Jaccard를 계산하고, `softmax(점수 / 0.05)`의 최댓값이 **0.2를 넘을 때만** 그 문서를 인용한다.

- **겹치는 keyword가 없으면** 모든 점수가 0 → softmax가 균등(문서 15개면 각 0.067, 5개면 0.2) → 0.2를 넘지 못해 **인용하지 않음**.
- **keyword가 겹치면** temperature 0.05 때문에 확률이 그 문서로 몰려 대부분 **인용**. 예: 문서 15개 기준 최고 Jaccard 0.1이면 확률 0.35(인용), 0.05면 0.16(생략).
- 실질 규칙: **"문서와 의미 있는 keyword가 하나라도 겹치면 인용, 아니면 생략."**

예시 (공저자 원본 CovidDialog 결과, Llama2 Chat, 첫 대화):

| 문장 | 비교 baseline(`vanilla_output`) | 제안 방법(`kw_jaccard_output`) |
| --- | --- | --- |
| "Thank you for reaching out with your concern." | (Medline: Peginterferon Alfa-2b Injection) — 무관한 인용 | 인용 없음 |
| "It's understandable to feel uncertain about taking antibiotics…" | (Koren, 2010) | 인용 없음 |

### 3.2 dense · SPLADE와의 차이
- dense(코사인)와 SPLADE(내적) 점수는 관련 없는 문장–문서 사이에서도 0이 되지 않는다. argmax로 고르면 **모든 문장에 인용이 붙는다** (ALCE `post_hoc_cite.py`도 매 문장 인용).
- 이들에도 threshold를 걸 수는 있지만, "관련 없음"을 뜻하는 **자연스러운 기준점이 없어** 데이터마다 보정해야 한다.
- keyword 매칭은 **"겹치는 keyword 0개"라는 해석 가능한 기준점**을 갖는다. 논문 Table 5에서 threshold 0.15–0.25 사이 결정이 93.8% 이상 동일하다고 보고한 것도 이 성질 덕분.
- 정확한 표현: "다른 방법은 불가능하다"가 아니라 **"별도 보정 없이 기권 신호를 자연스럽게 갖는다."**

### 3.3 실제로 얼마나 일어나나

**위키 QA (M2, threshold 0.2)** — 거의 일어나지 않고, 일어나면 손해:

| | 전체 단위 | 인용 생략 | 생략된 예 |
| --- | ---: | ---: | --- |
| ASQA | 127문장 | 3 (2.4%) | "The 14th season premiered on September 28, 2017." |
| QAMPARI | 528개 답 | 41 (7.8%) | "Superfamily database", "Scholar Extraordinary" |

- 생략된 것은 인사말이 아니라 **인용이 필요한 사실 문장**이다. keyword 추출기가 겹치는 keyword를 찾지 못한 경우.
- 그래서 ASQA 점수가 threshold 0.2에서 떨어졌다 (53.3 → 51.8). ALCE 지표도 인용 없는 문장을 감점한다.

**의료 대화 (CovidDialog, 기존 결과)** — 효과가 나는 곳:
- 의사 답변에는 인사말, 공감, 일반 조언이 섞여 있어 이런 문장에 인용하지 않는 것이 실제로 올바른 행동이다.
- 사람 평가(Table 2: 2.88 vs 1.83)와 GPT-4 평가(Table 1: Llama2-7B Chat 2.58 vs 2.09)에서 제안 방법이 이긴 주된 이유로 보인다.

### 3.4 약점
1. **평가 기준이 이 성질을 보상하도록 설계됐다.** 논문 Fig. 7–8의 평가 지시문에 "인사말에 인용하지 않는 것이 옳다, 불필요한 인용은 감점"이 명시돼 있다. 리뷰어가 "평가를 방법에 유리하게 만들었다"고 볼 여지가 있다. 다만 기준 자체는 합리적이고 사람 평가자도 같은 결론을 냈다.
2. **비교 상대가 약했을 수 있다.** CovidDialog baseline이 gtr-t5-xxl이 아니라 bert-base였을 가능성이 있다(`run_2.sh`, `rebuttal_plan.md` 확정 사항 5번). SPLADE와는 비교한 적이 없다.
3. **인용 누락과 구별되지 않는다.** 같은 규칙이 위키 QA에서는 필요한 인용을 빠뜨렸다(3.3).

### 3.5 소구점으로 확정하려면: A2 재개
CovidDialog 61건(공저자 원본 답변 · 건당 문서 15개)에서 **제안 방법(threshold 0.2), SPLADE, dense(gtr-t5-xxl)**을 같은 조건으로 다시 비교한다.
- **평가**: gpt-4o-mini, 기존 프롬프트 그대로 쌍대 비교 (A/B 순서 교체, 3회 반복). 예상 비용 약 $4. OpenAI 키 준비됨.
- **보조 지표**: 인사말·공감 문장에 붙은 인용 비율을 방법별로 직접 센다. GPT 평가 없이도 "불필요한 인용을 얼마나 줄이는가"를 객관적으로 보여 준다.
- **결과에 따른 분기**:
  - 좋으면: "대화형 RAG에서 불필요한 인용을 줄이면서, dense보다 훨씬 가볍다"를 소구점으로 쓴다.
  - 나쁘면: 소구점을 ①과 ③으로 좁힌다.
- 설계 상세는 `rebuttal_plan.md` "범위 제외" 아래 "참고: A2를 다시 넣을 경우의 설계".

## 4. 재서술 방향 (안)

| 주장 | 처리 |
| --- | --- |
| dense 임베딩보다 정확하다 | ❌ 삭제. 위키 QA에서 SPLADE·dense가 더 높음을 인정 |
| keyword 선택이 성능을 만든다 | ❌ 삭제 또는 약화. E1을 ablation으로 그대로 보고 |
| dense MIPS(gtr-t5-xxl)보다 훨씬 가볍고 빠르다 | ✅ 유지 (keyword 추출 포함 수치로) |
| 인용 근거를 해석할 수 있다 | ✅ 유지 |
| 인용이 필요한 문장만 인용한다 | 🔶 A2 결과에 따라 |
| 생성기 자체 인용보다 낫다 | 🔶 사실로만 진술, 내세우지 않음 |
| "requires no neural inference" | ✏️ "유사도 계산은 신경망 추론 없이 집합 연산만 쓰며, keyword 추출에 경량 BERT/BioBERT를 쓴다"로 한정 |

SPLADE 결과는 숨기지 않고, 논문 §6 Future work가 이미 언급한 "SPLADE식 확장을 keyword 인용에 접목"하는 방향으로 연결한다.

## 5. 공저자 · 지도교수와 논의할 질문

1. 소구점을 ①+③(+②) 방향으로 바꾸는 데 동의하는가?
2. A2(CovidDialog 재비교)를 재개해 ②를 확인할 것인가? (비용 약 $4, 반나절)
3. §5.2 baseline 서술을 어떻게 정정할 것인가? Table 1 baseline이 VANILLA였던 경위 확인이 필요하다.
4. SPLADE가 정확도·속도 모두 앞선 결과를 rebuttal letter에서 어떻게 설명할 것인가?
5. 공저자 확인 사항: CovidDialog GPT-4 점수가 어느 컬럼(`jaccard_output` / `kw_jaccard_output`)으로 나왔는지, CovidDialog baseline encoder, `asqa_comp.pkl`의 `ours_*` 의미.

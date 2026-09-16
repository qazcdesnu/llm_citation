# Reviewer's Comment

## Raw Comment

핵심 주장에 대한 실험들이 여전히 부족합니다. 예를 들어, 문장을 생성한 후, BM25로만 또는 TF-IDF로만 비교한다거나, full-token Jaccard, SPLADE 등과도 비교실험이 포함되어야 합니다. 또는 ablation study에서 각 단계별 뺐을 때, 제안한 방법들의 성능 하락이 어떻게 되는지 보여줄 필요가 있습니다. 일부 표현들, "the proposed citation method requires no neural inference"이라는 것은 적절치 않습니다. 왜냐하면 제안한 방법은 BERT/BioBERT를 돌려서 keyword를 추출하는데, 이 또한 neural inference를 사용하기 때문입니다. 그리고, 2025년도 ACL Industry 논문으로 CiteFix: Enhancing RAG Accuracy Through Post-Processing Citation Correction이 있으며, 이 방법과 비교를 할 필요가 있어 보입니다.

## Points

| No. | Problem                                             | Proposed solution                                                                                               | Our solution |
| --- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------ |
| 1   | Insufficient experiments to support the core claims | add experiments(comparison to full-token Jaccard and SPLADE)                                                    |              |
| 2   | lack of ablation study                              |                                                                                                                 |              |
| 3   | inappropriate expression                            | correct expression like "the proposed citation method requires no neural inference"                             |              |
| 4   | insufficient citation related works                 | comparison to "CiteFix: Enhancing RAG Accuracy Through Post-Processing Citation Correction"(2025, ACL Industry) |              |



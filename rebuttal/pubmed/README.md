# PubMed 2023 baseline (MedDialog retrieval corpus)

`code/code/VectorDB/pubmed_download.py` fetched `pubmed23n*.xml.gz` from the NCBI FTP.
Those files no longer exist there: NCBI keeps only the current year (`pubmed26n*` as of
2026-09), and the NLM MEDLINE/PubMed Baseline Repository (`mbr.nlm.nih.gov`) no longer
resolves. The original script also starts at `pubmed23n0000`, which never existed.

## Source

The Internet Archive captured the NCBI FTP on 2023-12-02..10, just before the 2024
baseline replaced it. Checked 2026-09-28 via the Wayback CDX API:

- 1165 of 1166 `.xml.gz` files and all `.md5` files are archived.
- `pubmed23n0673.xml.gz` is **not** archived (only a failed capture); its `.md5` is.
- `pubmed23n0001.xml.gz` was downloaded and matched NLM's md5 (`acef800b…`),
  30,000 `<PubmedArticle>` records, so the archive serves the original bytes.
- Total compressed size ≈ 41 GB (sum of CDX record sizes).

## Run

```bash
cd rebuttal && mkdir -p slurm_log
sbatch pubmed/download_pubmed23.sbatch
tail -f slurm_log/pubmed23-dl-<jobid>.out
```

Output: `/shared/s3/lab03/jinwoongkim/pubmed/baseline23/`, plus `download_status.json`
(verified count, failed ids). Verified files are skipped on re-run, so resubmit after a
timeout or if `failed` is non-empty.

## pubmed23n0673

Baseline files are split by PMID. Take the last PMID of 0672 and the first PMID of 0674,
then pull the records in that range from the 2026 baseline. They can differ from the
2023 versions where NLM revised a record since, and records deleted before 2026 are
absent. About 30k records, under 0.1% of the corpus; state this in the rebuttal.

## Still unknown

The paper's index is named `pubmed_medline_year_partial_bge-large`, but no code filters
by year or takes a partial file set (`vector_store.py` saves `..._year_all_...`).
Ask the co-author what "partial" meant before building the index.

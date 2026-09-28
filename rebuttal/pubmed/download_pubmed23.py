"""Download the PubMed 2023 annual baseline (pubmed23n0001-1166) from the Wayback Machine.

NCBI keeps only the current year's baseline on its FTP and the old MEDLINE/PubMed
Baseline Repository (mbr.nlm.nih.gov) no longer resolves, so the corpus behind
code/code/VectorDB is gone from official sources. The Internet Archive captured
the NCBI FTP on 2023-12-02..10, just before the 2024 baseline replaced it:
1165 of 1166 files plus their .md5 files. pubmed23n0673.xml.gz was not captured
(only its .md5 was); see README.md in this directory for the replacement plan.

Every file is checked against NLM's own .md5, so a verified file is byte-identical
to the original. Re-running skips verified files, so an interrupted job resumes.

Standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# `id_` returns the archived bytes without the Wayback toolbar; `2023` picks the
# closest 2023 capture. The double slash is part of the archived URL.
BASE = "https://web.archive.org/web/2023id_/https://ftp.ncbi.nlm.nih.gov//pubmed/baseline"
N_FILES = 1166
NOT_ARCHIVED = {673}  # CDX shows only a failed capture for the .xml.gz
UA = "llm-citation-rebuttal/1.0 (research reproduction; single user)"


def name(i: int) -> str:
    return f"pubmed23n{i:04d}.xml.gz"


def fetch(url: str, dest: Path, timeout: int) -> None:
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    tmp.replace(dest)


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def expected_md5(md5_file: Path) -> str:
    # NLM format: "MD5(pubmed23n0001.xml.gz)= acef800b..."
    return md5_file.read_text().strip().split("=")[-1].strip()


def verified(out: Path, i: int) -> bool:
    gz, md5 = out / name(i), out / (name(i) + ".md5")
    return gz.exists() and md5.exists() and md5_of(gz) == expected_md5(md5)


def get_one(out: Path, i: int, retries: int, timeout: int) -> tuple[int, str]:
    gz, md5 = out / name(i), out / (name(i) + ".md5")
    if verified(out, i):
        return i, "skip"
    last = ""
    for attempt in range(retries):
        try:
            if not md5.exists():
                fetch(f"{BASE}/{md5.name}", md5, timeout)
            if i in NOT_ARCHIVED:
                return i, "md5-only"
            fetch(f"{BASE}/{gz.name}", gz, timeout)
            if md5_of(gz) == expected_md5(md5):
                return i, "ok"
            last = "md5 mismatch"
            gz.unlink(missing_ok=True)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}"
        except Exception as e:  # network resets, timeouts
            last = f"{type(e).__name__}: {e}"
        # archive.org throttles bursts (429/503); back off with jitter
        time.sleep(min(300, 15 * 2 ** attempt) + random.uniform(0, 5))
    return i, f"FAILED ({last})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="download directory")
    ap.add_argument("--workers", type=int, default=3, help="keep small: archive.org rate-limits")
    ap.add_argument("--retries", type=int, default=6)
    ap.add_argument("--timeout", type=int, default=600, help="seconds per request")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=N_FILES)
    a = ap.parse_args()

    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    ids = range(a.start, a.end + 1)
    status: dict[int, str] = {}
    t0 = time.time()

    with ThreadPoolExecutor(a.workers) as ex:
        futs = [ex.submit(get_one, out, i, a.retries, a.timeout) for i in ids]
        for n, fut in enumerate(as_completed(futs), 1):
            i, s = fut.result()
            status[i] = s
            if s != "skip":
                print(f"[{n}/{len(futs)}] {name(i)} {s}  ({time.time() - t0:.0f}s)", flush=True)

    failed = sorted(i for i, s in status.items() if s.startswith("FAILED"))
    summary = {
        "verified": sum(s in ("ok", "skip") for s in status.values()),
        "md5_only_not_archived": sorted(i for i, s in status.items() if s == "md5-only"),
        "failed": failed,
        "elapsed_s": round(time.time() - t0),
    }
    (out / "download_status.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

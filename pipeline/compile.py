import logging
import os
import re
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
from smart_open import open as smart_open

from pipeline.config import DOWNLOAD_WORKERS, PROCESS_WORKERS

log = logging.getLogger(__name__)

_s3_client = None
_PUBLIC_TYPE_RE = re.compile(r"\bpublic\s+(?:class|interface|enum|record)\s+(\w+)")


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        session = boto3.Session(
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        )
        _s3_client = session.client("s3")
    return _s3_client


def download_content(row: dict) -> str | None:
    blob_id  = row["blob_id"]
    encoding = row.get("src_encoding", "utf-8") or "utf-8"
    s3_url   = f"s3://softwareheritage/content/{blob_id}"
    try:
        with smart_open(s3_url, "rb", compression=".gz",
                        transport_params={"client": _get_s3_client()}) as fin:
            return fin.read().decode(encoding, errors="replace")
    except Exception as exc:
        log.debug("S3 download failed for %s: %s", blob_id, exc)
        return None


def download_batch(rows: list[dict]) -> list[tuple[dict, str]]:
    results = []
    with ThreadPoolExecutor(max_workers=DOWNLOAD_WORKERS) as executor:
        futures = {executor.submit(download_content, row): row for row in rows}
        for future in as_completed(futures):
            source = future.result()
            if source is not None:
                results.append((futures[future], source))
    return results


def compiles(source: str) -> bool:
    match    = _PUBLIC_TYPE_RE.search(source)
    filename = (match.group(1) if match else "Main") + ".java"
    with tempfile.TemporaryDirectory() as tmpdir:
        java_file = Path(tmpdir) / filename
        java_file.write_text(source, encoding="utf-8")
        result = subprocess.run(
            ["javac", str(java_file)],
            capture_output=True,
            timeout=30,
        )
    return result.returncode == 0


def compile_batch(items: list[tuple[dict, str]]) -> list[tuple[dict, str]]:
    results = []
    with ThreadPoolExecutor(max_workers=PROCESS_WORKERS) as executor:
        futures = {executor.submit(compiles, source): (row, source) for row, source in items}
        for future in as_completed(futures):
            if future.result():
                results.append(futures[future])
    return results

import logging
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from pipeline.config import CHECKSTYLE_JAR, CHECKSTYLE_CFG, PROCESS_WORKERS

log = logging.getLogger(__name__)


def passes_checkstyle(source: str) -> bool:
    with tempfile.TemporaryDirectory() as tmpdir:
        java_file = Path(tmpdir) / "Check.java"
        java_file.write_text(source, encoding="utf-8")
        result = subprocess.run(
            ["java", "-jar", CHECKSTYLE_JAR, "-c", CHECKSTYLE_CFG, str(java_file)],
            capture_output=True,
            timeout=30,
        )
    return result.returncode == 0


def lint_batch(items: list[tuple[dict, str]]) -> list[tuple[dict, str]]:
    results = []
    with ThreadPoolExecutor(max_workers=PROCESS_WORKERS) as executor:
        futures = {executor.submit(passes_checkstyle, source): (row, source) for row, source in items}
        for future in as_completed(futures):
            if future.result():
                results.append(futures[future])
    return results

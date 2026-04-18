import logging

from tqdm import tqdm

from pipeline.config import BATCH_SIZE, MAX_OUTPUT_BYTES, MAX_OUTPUT_GB
from pipeline.fetch import stream_java_files
from pipeline.filter import prefilter_stream, drop_filter_columns
from pipeline.compile import download_batch, compile_batch
from pipeline.lint import lint_batch
from pipeline.rewrite import load_model, sgcr_rewrite
from pipeline.output import flush_batch, finalize_and_push

log = logging.getLogger(__name__)


def _collect_batch(iterator, size: int) -> list:
    batch = []
    for item in iterator:
        batch.append(item)
        if len(batch) >= size:
            break
    return batch


def run_pipeline() -> None:
    llm         = load_model()
    java_stream = prefilter_stream(stream_java_files())

    counts      = {"fetched": 0, "compiled": 0, "linted": 0, "rewritten": 0}
    total_bytes = 0
    shard_idx   = 0
    done        = False

    pbar = tqdm(desc="Pipeline", unit=" files")
    while not done:
        raw_batch = _collect_batch(java_stream, BATCH_SIZE)
        if not raw_batch:
            break
        counts["fetched"] += len(raw_batch)
        pbar.update(len(raw_batch))

        downloaded = download_batch(raw_batch)
        compiled   = compile_batch(downloaded)
        counts["compiled"] += len(compiled)

        linted = lint_batch(compiled)
        counts["linted"] += len(linted)

        batch_results = []
        for row, source in linted:
            rewritten    = sgcr_rewrite(source, llm)
            row_bytes    = len(source.encode()) + len(rewritten.encode())
            total_bytes += row_bytes
            counts["rewritten"] += 1

            batch_results.append({
                **drop_filter_columns(row),
                "content":           source,
                "rewritten_content": rewritten,
            })

            if MAX_OUTPUT_BYTES and total_bytes >= MAX_OUTPUT_BYTES:
                log.info("Reached MAX_OUTPUT_GB=%.1f (%.2f GB collected), stopping.",
                         MAX_OUTPUT_GB, total_bytes / 1024 ** 3)
                done = True
                break

        if batch_results:
            flush_batch(batch_results, shard_idx)
            shard_idx += 1

        pbar.set_postfix({**counts, "size_gb": f"{total_bytes / 1024**3:.2f}"})

    pbar.close()
    log.info("Final counts: %s", counts)
    finalize_and_push()

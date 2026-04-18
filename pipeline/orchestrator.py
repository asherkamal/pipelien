import logging
import queue
import threading

from tqdm import tqdm

from pipeline.config import BATCH_SIZE, PREFETCH_BATCHES, MAX_OUTPUT_BYTES, MAX_OUTPUT_GB
from pipeline.fetch import stream_java_files
from pipeline.filter import prefilter_stream, drop_filter_columns
from pipeline.compile import download_batch, compile_batch
from pipeline.lint import lint_batch
from pipeline.rewrite import load_model, sgcr_rewrite
from pipeline.output import flush_batch

log = logging.getLogger(__name__)

_SENTINEL = None


def _collect_batch(iterator, size: int) -> list:
    batch = []
    for item in iterator:
        batch.append(item)
        if len(batch) >= size:
            break
    return batch


def _producer(java_stream, counts: dict, out_queue: queue.Queue, stop: threading.Event) -> None:
    """Background thread: fetch → download → compile → lint → enqueue batches for the LLM."""
    try:
        while not stop.is_set():
            raw_batch = _collect_batch(java_stream, BATCH_SIZE)
            if not raw_batch:
                break
            counts["fetched"] += len(raw_batch)

            downloaded = download_batch(raw_batch)
            compiled   = compile_batch(downloaded)
            counts["compiled"] += len(compiled)

            linted = lint_batch(compiled)
            counts["linted"] += len(linted)

            if linted:
                out_queue.put(linted)  # blocks when queue is full, backpressuring the producer
    finally:
        out_queue.put(_SENTINEL)


def run_pipeline() -> None:
    llm         = load_model()
    java_stream = prefilter_stream(stream_java_files())

    counts      = {"fetched": 0, "compiled": 0, "linted": 0, "rewritten": 0}
    total_bytes = 0
    shard_idx   = 0

    prefetch_queue = queue.Queue(maxsize=PREFETCH_BATCHES)
    stop_event     = threading.Event()
    producer_thread = threading.Thread(
        target=_producer,
        args=(java_stream, counts, prefetch_queue, stop_event),
        daemon=True,
    )
    producer_thread.start()

    pbar = tqdm(desc="Pipeline", unit=" files")
    done = False
    while not done:
        linted_batch = prefetch_queue.get()
        if linted_batch is _SENTINEL:
            break

        batch_results = []
        for row, source in linted_batch:
            rewritten    = sgcr_rewrite(source, llm)
            row_bytes    = len(source.encode()) + len(rewritten.encode())
            total_bytes += row_bytes
            counts["rewritten"] += 1
            pbar.update(1)

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

    stop_event.set()
    producer_thread.join()
    pbar.close()
    log.info("Final counts: %s", counts)
    log.info("Run finalize.py when ready to concatenate shards and push to the Hub.")

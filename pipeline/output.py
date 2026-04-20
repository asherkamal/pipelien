import glob
import logging
import os

from datasets import Dataset, concatenate_datasets, load_from_disk
from transformers import AutoTokenizer

from pipeline.config import OUTPUT_DIR, HF_REPO_ID, HF_TOKEN

log = logging.getLogger(__name__)

_SHARDS_DIR = os.path.join(OUTPUT_DIR, "shards")


def flush_batch(rows: list[dict], shard_idx: int) -> None:
    shard_dir = os.path.join(_SHARDS_DIR, f"{shard_idx:05d}")
    Dataset.from_list(rows).save_to_disk(shard_dir)
    log.info("Flushed shard %05d (%d rows)", shard_idx, len(rows))


def finalize_and_push() -> None:
    shard_dirs = sorted(glob.glob(os.path.join(_SHARDS_DIR, "*")))
    if not shard_dirs:
        log.warning("No shards found — nothing to finalize.")
        return

    log.info("Concatenating %d shards...", len(shard_dirs))
    ds = concatenate_datasets([load_from_disk(d) for d in shard_dirs])
    final_dir = os.path.join(OUTPUT_DIR, "final")
    ds.save_to_disk(final_dir)
    log.info("Final dataset: %d rows → %s", len(ds), final_dir)

    log.info("Counting tokens with Qwen tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct", token=HF_TOKEN)
    total_tokens = sum(
        len(tokenizer.encode(r["content"])) + len(tokenizer.encode(r["rewritten_content"]))
        for r in ds
    )
    log.info("Total tokens: %s (~%.1fM)", f"{total_tokens:,}", total_tokens / 1_000_000)

    if not HF_REPO_ID:
        log.warning("HF_REPO_ID is not set — skipping HuggingFace push.")
        return

    log.info("Pushing to HuggingFace Hub: %s", HF_REPO_ID)
    ds.push_to_hub(HF_REPO_ID, token=HF_TOKEN)
    log.info("Published at https://huggingface.co/datasets/%s", HF_REPO_ID)

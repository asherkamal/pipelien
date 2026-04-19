import logging
from datasets import load_dataset
from pipeline.config import HF_TOKEN

log = logging.getLogger(__name__)


def stream_java_files():
    log.info("Loading bigcode/the-stack-v2-dedup (streaming, Java only)...")
    ds = load_dataset(
        "bigcode/the-stack-v2-dedup",
        "Java",
        split="train",
        streaming=True,
        trust_remote_code=True,
        token=HF_TOKEN,
    )
    return ds

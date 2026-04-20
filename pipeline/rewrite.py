import logging
import os
import re

from huggingface_hub import hf_hub_download
from llama_cpp import Llama

from pipeline.config import GGUF_MODEL_REPO, GGUF_MODEL_FILE, GGUF_MODEL_PATH, HF_TOKEN, SGCR_PROMPT

log = logging.getLogger(__name__)


def load_model() -> Llama:
    model_path = GGUF_MODEL_PATH
    if not os.path.exists(model_path):
        log.info("Downloading GGUF model %s/%s...", GGUF_MODEL_REPO, GGUF_MODEL_FILE)
        hf_hub_download(
            repo_id=GGUF_MODEL_REPO,
            filename=GGUF_MODEL_FILE,
            token=HF_TOKEN,
            local_dir=os.path.dirname(model_path),
        )
    log.info("Loading GGUF model from %s...", model_path)
    return Llama(
        model_path=model_path,
        n_gpu_layers=-1,
        n_ctx=16384,
        verbose=False,
    )


_MAX_SOURCE_CHARS = 48_000  # ~12k tokens — 16k ctx minus 4k output and ~120 token prompt overhead


def sgcr_rewrite(source: str, llm: Llama) -> str | None:
    if len(source) > _MAX_SOURCE_CHARS:
        log.debug("Skipping file: %d chars exceeds limit", len(source))
        return None
    try:
        response = llm.create_chat_completion(
            messages=[{"role": "user", "content": SGCR_PROMPT.format(code=source)}],
            max_tokens=12288,
            temperature=0,
        )
    except ValueError as exc:
        log.warning("LLM error, skipping file: %s", exc)
        return None
    choice = response["choices"][0]
    if choice["finish_reason"] == "length":
        log.warning("Output truncated (hit max_tokens) for file with %d chars — consider raising max_tokens", len(source))
    generated = choice["message"]["content"]
    fence_match = re.search(r"```(?:java)?\n(.*?)```", generated, re.DOTALL)
    return fence_match.group(1).strip() if fence_match else generated.strip()

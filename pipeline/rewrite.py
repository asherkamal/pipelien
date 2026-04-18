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
        model_path = hf_hub_download(
            repo_id=GGUF_MODEL_REPO,
            filename=GGUF_MODEL_FILE,
            token=HF_TOKEN,
        )
    log.info("Loading GGUF model from %s...", model_path)
    return Llama(
        model_path=model_path,
        n_gpu_layers=-1,
        n_ctx=8192,
        verbose=False,
    )


def sgcr_rewrite(source: str, llm: Llama) -> str:
    response = llm.create_chat_completion(
        messages=[{"role": "user", "content": SGCR_PROMPT.format(code=source)}],
        max_tokens=4096,
        temperature=0,
    )
    generated = response["choices"][0]["message"]["content"]
    fence_match = re.search(r"```(?:java)?\n(.*?)```", generated, re.DOTALL)
    return fence_match.group(1).strip() if fence_match else generated.strip()

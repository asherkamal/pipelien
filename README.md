Java Style Rewrite Pipeline
Streams Java source files from [bigcode/the-stack-v2-dedup](https://huggingface.co/datasets/bigcode/the-stack-v2-dedup), rewrites them to conform to the Google Java Style Guide using a local LLM, and saves the result as a HuggingFace dataset.

1. **Streams** Java files from The Stack v2 (deduplicated)
2. **Filters** out generated files, non-UTF-8, and non-`.java` extensions
3. **Downloads & compiles** each batch to verify the code is valid Java
4. **Lints** with Checkstyle against a custom config
5. **Rewrites** each file using [Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF) (GGUF, 4-bit) to apply Google Java Style
6. **Saves shards** to `output_dataset/shards/` as HuggingFace datasets
7. **Finalizes** by concatenating shards and optionally pushing to the Hub

Requirements:

- [Git](https://git-scm.com/downloads)
- [Docker](https://docs.docker.com/get-docker/)
- [Python 3.10+](https://www.python.org/downloads/) and pip (only needed to run `finalize.py` locally)
- NVIDIA GPU with drivers installed
- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- A HuggingFace account with access to `bigcode/the-stack-v2-dedup`

## Installation

Clone repo:
git clone https://github.com/your-username/your-repo.git

.env:
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
HF_TOKEN= hugging face token
HF_REPO_ID= hugging face repo for pushing to Hub
MAX_OUTPUT_GB= stop streaming/processing data after N gb
BATCH_SIZE
DOWNLOAD_WORKERS
PROCESS_WORKERS
PREFETCH_BATCHES

Install dependencies (for finalize.py):
pip install -r requirements.txt

Run:
docker compose build #Build the Docker image
docker compose up #Start the pipeline
docker compose down #stop the pipeline

Logs stream directly to your terminal. Output shards are written to `output_dataset/shards/` on your host machine.

Once the pipeline finishes (or you stop it early), run 'python finalize.py' to concatenate shards and optionally push to HuggingFace Hub:
This merges all shards into `output_dataset/final/` and pushes to `HF_REPO_ID` if set.

## Output schema

| Column                          | Description                                         |
| ------------------------------- | --------------------------------------------------- |
| `content`                       | Original Java source                                |
| `rewritten_content`             | Google Java Style rewritten version                 |
| + all original Stack v2 columns | (minus `is_generated`, `src_encoding`, `extension`) |

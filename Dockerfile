FROM nvidia/cuda:12.4.1-devel-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-21-jdk-headless \
        python3-pip \
        cmake \
        ninja-build \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Long build step isolated so it caches independently of app code changes
RUN CMAKE_ARGS="-DGGML_CUDA=on" pip install --no-cache-dir llama-cpp-python

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY pipeline/ pipeline/
COPY checkstyle-config.xml .

RUN mkdir -p /app/output_dataset/shards /app/models /app/tools

CMD ["python3", "main.py"]

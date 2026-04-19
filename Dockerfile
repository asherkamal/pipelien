FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-21-jdk-headless \
        python3-pip \
        wget \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Long build step isolated so it caches independently of app code changes
RUN pip install --no-cache-dir \
    llama-cpp-python \
    --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu124

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY pipeline/ pipeline/
COPY checkstyle-config.xml .

RUN mkdir -p /app/output_dataset/shards /app/models /app/tools && \
    wget -q -O /app/tools/checkstyle.jar \
    https://github.com/checkstyle/checkstyle/releases/download/checkstyle-10.17.0/checkstyle-10.17.0-all.jar

CMD ["python3", "main.py"]

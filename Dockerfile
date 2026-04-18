FROM rocm/dev-ubuntu-22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-21-jdk-headless \
        python3-pip \
        cmake \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Long build step isolated so it caches independently of app code changes
RUN CMAKE_ARGS="-DGGML_HIPBLAS=on" pip install --no-cache-dir llama-cpp-python

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY pipeline/ pipeline/
COPY checkstyle-config.xml .

RUN mkdir -p /app/output_dataset/shards /app/models /app/tools

CMD ["python3", "main.py"]

# --- Build stage: compiles llama-cpp-python and other native deps ---
FROM python:3.11-slim-bookworm AS builder

# Configure apt for reliable downloads with retries and timeouts
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries && \
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80retries

# Build-only tools needed to compile llama-cpp-python; not shipped in the final image
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    build-essential \
    cmake \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --default-timeout=1000 --retries 20 --prefix=/install -r requirements.txt

# --- Runtime stage: only what's needed to run the app ---
FROM python:3.11-slim-bookworm

RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries && \
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80retries

# Runtime dependencies for OCR/PDF handling and the OpenMP runtime llama-cpp-python needs
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    tesseract-ocr \
    tesseract-ocr-deu \
    poppler-utils \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Unprivileged user the app runs as (see docker-entrypoint.sh)
RUN groupadd --system --gid 10001 app && \
    useradd --system --uid 10001 --gid app --home-dir /tmp --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

# Create volume directories; make sure the entrypoint has Unix line endings and is executable
# (a Windows checkout may have converted it).
RUN mkdir -p /app/data /app/documents /app/models_data && \
    sed -i 's/\r$//' /app/docker-entrypoint.sh && \
    chmod +x /app/docker-entrypoint.sh

# Unbuffered stdout so log lines (incl. the one-time initial admin password) show up
# in `docker compose logs` immediately instead of after the buffer fills.
# The code directory is read-only for the app user, so no bytecode caches; the model
# download cache lives on the models volume instead of a home directory.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOME=/tmp \
    HF_HOME=/app/models_data/.hf-cache

# Listen on loopback only: the Next.js frontend (same host network) is the one public
# entry point and proxies everything, so port 8000 must not be reachable from the LAN.
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000", "--no-proxy-headers"]

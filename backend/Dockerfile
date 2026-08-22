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

WORKDIR /app

COPY --from=builder /install /usr/local
COPY . .

# Create volume directories
RUN mkdir -p /app/data /app/documents /app/models_data

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

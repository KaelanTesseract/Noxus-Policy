FROM python:3.11-slim-bookworm

# Configure apt for reliable downloads with retries and timeouts
RUN echo 'Acquire::Retries "5";' > /etc/apt/apt.conf.d/80retries && \
    echo 'Acquire::http::Timeout "30";' >> /etc/apt/apt.conf.d/80retries

# Install system dependencies for OCR, PDF processing, and C++ compiler for embedded AI
RUN apt-get update && apt-get install -y --no-install-recommends --fix-missing \
    tesseract-ocr \
    tesseract-ocr-deu \
    poppler-utils \
    build-essential \
    cmake \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 --retries 5 -r requirements.txt

COPY . .

# Create volume directories
RUN mkdir -p /app/data /app/documents /app/models_data

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

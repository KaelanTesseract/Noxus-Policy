FROM python:3.11-slim

# Install system dependencies for OCR, PDF processing, and C++ compiler for embedded AI
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-deu \
    poppler-utils \
    build-essential \
    cmake \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=1000 --retries 10 -r requirements.txt

COPY . .

# Create volume directories
RUN mkdir -p /app/data /app/documents /app/models_data

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

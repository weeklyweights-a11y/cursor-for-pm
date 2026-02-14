FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Phase 5: CPU-only PyTorch first, then sentence-transformers from same index (avoids pulling CUDA)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
# Install deps except sentence-transformers so we can install it next with CPU torch index
RUN grep -v sentence-transformers requirements.txt > /tmp/req.txt && pip install --no-cache-dir -r /tmp/req.txt
# Install sentence-transformers preferring existing CPU torch (avoids pulling CUDA)
RUN pip install --no-cache-dir sentence-transformers \
    --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

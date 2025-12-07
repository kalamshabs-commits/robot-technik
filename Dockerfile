FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies for OpenCV/YOLO
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- 1. Dependencies ---
COPY requirements-server.txt /app/requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# --- 2. Code ---
COPY cloud_api/ /app/cloud_api/
COPY static/ /app/static/

# Copy Knowledge Base (Important!)
COPY faults_library.json /app/faults_library.json

# --- 3. Model ---
# Copy model to a standard location
RUN mkdir -p /app/models
COPY models/best.pt /app/models/best.pt
ENV YOLO_WEIGHTS_PATH=/app/models/best.pt

# --- 4. Run ---
ENV PORT=8080

# Use shell form to allow variable expansion ($PORT)
CMD uvicorn cloud_api.ai_main:app --host 0.0.0.0 --port ${PORT:-8080}

FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---- Install Python deps (server) ----
COPY requirements-server.txt /app/requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r /app/requirements.txt

# ---- Copy Flask app and assets ----
COPY flask_app.py /app/flask_app.py
COPY ai_helper.py /app/ai_helper.py
COPY diagnostic_engine.py /app/diagnostic_engine.py
COPY image_ai.py /app/image_ai.py
COPY faults_library.json /app/faults_library.json
COPY static/ /app/static/

# ---- Copy YOLO model ----
RUN mkdir -p /app/models
COPY models/best.pt /app/models/best.pt

ENV YOLO_WEIGHTS_PATH=/app/models/best.pt
ENV PORT=8080

EXPOSE 8080

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:${PORT}", "flask_app:app"]

FROM python:3.10-slim

# Установка библиотек для видео (чтобы OpenCV работал с твоей моделью)
RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

# Тут устанавливается ultralytics, чтобы читать твой best.pt
RUN pip install --no-cache-dir -r requirements.txt

# Было: CMD ["uvicorn", "cloud_api.ai_main:app", ...]
# СТАЛО (Это надежнее для путей):
CMD python -m uvicorn cloud_api.ai_main:app --host 0.0.0.0 --port${PORT:-8080}

# Используем Python 3.11
FROM python:3.11-slim

# Настройки окружения
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Установка системных библиотек (нужны для OpenCV/YOLO)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# --- 1. Установка зависимостей ---
# Убедитесь, что у вас файл называется requirements.txt (тот короткий, что я давал выше)
COPY requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt

# --- 2. Копирование кода ---
# Копируем папку с бэкендом (FastAPI)
COPY cloud_api/ /app/cloud_api/

# Копируем статику (Frontend)
COPY static/ /app/static/

# --- 3. Копирование модели ---
# Мы настроили python-код искать best.pt в корне или в папке cloud_api.
# Если у вас файл лежит в папке models локально, раскомментируйте первую строку:
# COPY models/best.pt /app/best.pt
# Если файл лежит в корне проекта локально, используйте эту строку:
COPY best.pt /app/best.pt

# --- 4. Запуск ---
ENV PORT=8080

# ВАЖНО: Запускаем uvicorn (сервер для FastAPI)
# cloud_api.ai_main:app означает:
# папка cloud_api -> файл ai_main.py -> переменная app внутри него
CMD ["uvicorn", "cloud_api.ai_main:app", "--host", "0.0.0.0", "--port", "8080"]
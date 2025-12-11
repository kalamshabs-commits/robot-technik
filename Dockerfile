# Используем Python 3.10
FROM python:3.10-slim

# Настройки Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Рабочая папка
WORKDIR /app

# --- 1. Установка системных библиотек (В ОДНУ СТРОКУ) ---
# Так редактор перестанет ругаться на отступы и пробелы
RUN apt-get update && apt-get install -y --no-install-recommends libgl1-mesa-glx libglib2.0-0 && rm -rf /var/lib/apt/lists/*

# --- 2. Установка зависимостей ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- 3. Копирование кода ---
COPY . .

# --- 4. Запуск ---
ENV PORT=8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

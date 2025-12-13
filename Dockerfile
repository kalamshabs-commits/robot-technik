FROM python:3.10-slim

# Установка системных библиотек для OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем список библиотек и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Открываем порт 8080
ENV PORT=8080

# Команда запуска
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
# Используем Python 3.10 (стабильный)
FROM python:3.10-slim

# Настройки: отключаем буферизацию (чтобы логи были видны сразу)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# --- ГЛАВНОЕ ИЗМЕНЕНИЕ ---
# Устанавливаем build-essential (компиляторы gcc) и библиотеки для OpenCV.
# Это решает 99% ошибок "Failed to build wheel" или "Command errored out".
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Обновляем pip (старый pip часто вызывает ошибки) и устанавливаем библиотеки
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта
COPY . .

# Указываем порт
ENV PORT=8080

# Запускаем сервер
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"] 

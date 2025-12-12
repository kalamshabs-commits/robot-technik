FROM python:3.10-slim

# Установка системных зависимостей для OpenCV и YOLO
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование зависимостей и установка
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Настройка порта (Google Cloud Run ожидает 8080)
ENV PORT=8080

# Запуск приложения
CMD streamlit run app_main.py --server.port=8080 --server.address=0.0.0.0
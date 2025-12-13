# Используем Python 3.10
FROM python:3.10-slim

# Отключаем буферизацию
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Установка системных утилит (для OpenCV)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Обновляем pip
RUN pip install --no-cache-dir --upgrade pip

# 3. ШАГ A: Ставим PyTorch (CPU версия - легкая) отдельно!
# Это самый тяжелый этап, делаем его первым.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. ШАГ B: Ставим OpenCV (Headless) отдельно!
RUN pip install --no-cache-dir opencv-python-headless

# 5. ШАГ C: Ставим Ultralytics (YOLO) отдельно!
# Она увидит, что torch уже стоит, и не будет качать его заново.
RUN pip install --no-cache-dir ultralytics

# 6. ШАГ D: Ставим остальные легкие библиотеки из файла
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. Копируем код и запускаем
COPY . .
ENV PORT=8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
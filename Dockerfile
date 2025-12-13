# Используем Python 3.10
FROM python:3.10-slim

# Настройки Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Установка системных библиотек (компиляторы + библиотеки для видео)
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 2. Обновляем pip
RUN pip install --no-cache-dir --upgrade pip

# 3. 🔥 САМОЕ ВАЖНОЕ: Сначала ставим легкий PyTorch (CPU)
# Это сэкономит 1.5 ГБ трафика и спасет сборку от ошибки
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# 4. Теперь копируем остальные требования и устанавливаем их
COPY requirements.txt .
# Ultralytics увидит, что torch уже стоит, и не будет качать тяжелый
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копируем код
COPY . .

# 6. Запуск
ENV PORT=8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
# 1. Берем готовый образ от создателей YOLO
# В нем уже установлены Python, PyTorch, OpenCV и Ultralytics.
# Это спасает нас от ошибки "Build failed" (нехватки памяти).
FROM ultralytics/ultralytics:latest-cpu

# 2. Устанавливаем рабочую папку внутри сервера
WORKDIR /app

# 3. Копируем файл со списком библиотек
COPY requirements.txt .

# 4. Устанавливаем библиотеки из списка
# (Здесь установятся pypdf, jinja2, aiofiles и всё остальное)
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копируем весь код твоего проекта
COPY . .

# 6. Указываем порт для Google Cloud
ENV PORT=8080

# 7. Запускаем сервер
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

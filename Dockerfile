# БЕРЕМ ГОТОВУЮ БАЗУ (В ней уже есть Python, PyTorch, YOLO)
FROM ultralytics/ultralytics:latest-cpu

WORKDIR /app

# Устанавливаем только легкие вещи для сайта
# Обрати внимание: мы НЕ ставим тут torch или opencv, они уже есть внутри!
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    requests \
    pillow \
    openai \
    reportlab \
    jinja2 \
    aiofiles

# Копируем твой код
COPY . .

# Запуск
ENV PORT=8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
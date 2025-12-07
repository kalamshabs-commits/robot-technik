import importlib, sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Пытаемся подгрузить старые модули, если они есть (для совместимости)
for m in ("diagnostic_engine", "image_ai", "recall_parser"):
    try:
        importlib.import_module(m)
    except Exception as e:
        print(f"{m} load fail:", e)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
import pathlib
import requests
import subprocess
import io  
from PIL import Image, ImageDraw
from .security import apply_security
# Импортируем функцию общения с ИИ
from ai_helper import ask_ai as _ask_ai

app = FastAPI()
apply_security(app)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# Подключаем папку static для картинок и стилей
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "static"), html=True), name="static")

# --- Глобальные переменные для модели ---
_model_ready = False
_model_dir = os.path.join(os.path.dirname(__file__), "..", "models")
_yolo_model = None
_icons_dir = os.path.join(os.path.dirname(__file__), "..", "static", "icons")

# Генерация иконок (чтобы приложение было красивым)
def _ensure_icons():
    try:
        os.makedirs(_icons_dir, exist_ok=True)
        # Создаем простые иконки, если их нет
        for size in (192, 512):
            path = os.path.join(_icons_dir, f"icon-{size}.png")
            if os.path.exists(path):
                continue
            img = Image.new("RGBA", (size, size), "#FFFFFF")
            d = ImageDraw.Draw(img)
            c = "#2196F3"
            d.rectangle((0, 0, size, size), fill="white")
            d.ellipse((size//4, size//4, size*3//4, size*3//4), fill=c)
            img.save(path, "PNG")
    except Exception:
        pass

_ensure_icons()

# Загрузка файла весов (.pt)
async def _ensure_model():
    global _model_ready
    if _model_ready:
        return
    pathlib.Path(_model_dir).mkdir(parents=True, exist_ok=True)
    
    # Пути к файлам
    target_path = os.path.join(_model_dir, "best.pt")
    default_path = os.path.join(_model_dir, "yolov8n.pt")
    env_path = os.environ.get("YOLO_WEIGHTS_PATH", "")
    
    # 1. Если путь задан в переменной окружения и файл существует
    if env_path and os.path.exists(env_path):
        os.environ["YOLO_WEIGHTS_PATH"] = env_path
        _model_ready = True
        print(f"Model loaded from ENV: {env_path}")
        return

    # 2. Если файл уже есть в папке models (мы его запушили через git)
    if os.path.exists(target_path):
        os.environ["YOLO_WEIGHTS_PATH"] = target_path
        _model_ready = True
        print(f"Model loaded locally: {target_path}")
        return

    # 3. Если ничего нет — качаем стандартную модель (как заглушку)
    if not os.path.exists(default_path):
        print("Скачиваю стандартную модель YOLOv8n...")
        try:
            url = "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"
            r = requests.get(url, timeout=60)
            with open(default_path, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print("Ошибка скачивания модели:", e)
    
    os.environ["YOLO_WEIGHTS_PATH"] = default_path
    _model_ready = True
    print("Model loaded: default yolov8n.pt")

# Инициализация YOLO
def _ensure_yolo_model():
    global _yolo_model
    if _yolo_model is not None:
        return
    from ultralytics import YOLO
    
    # Берем путь, который установили в _ensure_model
    wp = os.environ.get("YOLO_WEIGHTS_PATH")
    if not wp or not os.path.exists(wp):
        # Фолбэк на стандартную, если что-то пошло не так
        wp = os.path.join(_model_dir, "yolov8n.pt")
        
    print(f"Loading YOLO from: {wp}")
    try:
        _yolo_model = YOLO(wp)
    except Exception as e:
        print(f"Critical error loading YOLO: {e}")
        # Пытаемся загрузить хоть что-то
        _yolo_model = YOLO("yolov8n.pt")

# ==========================================
# 🧠 УМНАЯ ДИАГНОСТИКА (ИСПРАВЛЕНО)
# ==========================================
@app.post("/ai/classify")
async def classify(file: UploadFile = File(...)):
    await _ensure_model()
    _ensure_yolo_model()
    
    # Читаем картинку
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return {"error": "Файл не является изображением"}
    
    try:
        # 1. Распознаем объект через YOLO
        # conf=0.25 — порог уверенности (можно менять)
        results = _yolo_model.predict(source=img, conf=0.25, verbose=False)
        r0 = results[0]
        
        found_objects = []
        best_object_name = None
        max_conf = 0.0

        # Собираем все, что нашли
        for box in r0.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            name = _yolo_model.names[cls_id]
            
            found_objects.append({"class": name, "confidence": conf})
            
            # Ищем самый вероятный объект
            if conf > max_conf:
                max_conf = conf
                best_object_name = name

        # 2. Генерируем УМНЫЙ ОТВЕТ через DeepSeek/OpenAI
        checklist = []
        
        if best_object_name:
            # Если нашли прибор -> спрашиваем ИИ
            print(f"Распознан объект: {best_object_name}. Запрашиваю чек-лист у ИИ...")
            
            try:
                # Формируем запрос для ИИ
                prompt = (
                    f"Я загрузил фото устройства, это похоже на {best_object_name}. "
                    "Напиши короткий чек-лист (3-4 пункта) для диагностики основных неисправностей этого прибора. "
                    "Отвечай только пунктами, без лишних слов."
                )
                
                # Вызываем функцию из ai_helper.py
                ai_response = _ask_ai(prompt, device_type=best_object_name)
                
                # Превращаем текст от ИИ в список строк для красивого вывода
                # Разделяем по переносам строк и убираем лишние знаки
                checklist = [
                    line.strip("- *1234567890.") 
                    for line in ai_response.split('\n') 
                    if len(line.strip()) > 5
                ]
            except Exception as e:
                print(f"Ошибка ИИ: {e}")
                checklist = [f"Обнаружен {best_object_name}. Проверьте питание.", "Осмотрите корпус на повреждения."]
        else:
            # Если ничего не нашли
            best_object_name = "Неизвестное устройство"
            checklist = ["Попробуйте сделать фото четче.", "Убедитесь, что прибор хорошо освещен."]

        # 3. Возвращаем ответ приложению
        return {
            "summary": f"Распознано: {best_object_name}",
            "diagnosisChecklist": checklist,  # <-- Сюда попадает ответ от ИИ
            "repairChecklist": [],
            "suspectNodes": found_objects,
            "timeEstimateMinutes": {"min": 10, "max": 30},
            "risks": [],
            "classes": []
        }

    except Exception as e:
        print("Ошибка в classify:", e)
        return {"error": "Ошибка обработки изображения"}


# ==========================================
# 💬 ЧАТ (ИСПРАВЛЕНО)
# ==========================================
@app.get("/ai/ask")
async def ask_page():
    return HTMLResponse(content="<h1>Чат-бот работает. Используйте интерфейс приложения.</h1>")

@app.post("/ai/ask")
async def ask(request: Request):
    # Получаем данные (JSON или форма)
    ct = request.headers.get("content-type", "")
    if "application/json" in ct:
        payload = await request.json()
    else:
        form = await request.form()
        payload = dict(form)
    
    question = payload.get("question", "")
    device_type = payload.get("device_type", "")
    history = payload.get("chat_history", [])

    if not question.strip():
        return {"answer": "Пожалуйста, напишите ваш вопрос."}

    # Формируем историю переписки для контекста
    context = ""
    if history:
        for msg in history[-5:]: # Берем последние 5 сообщений
            role = msg.get("role", "user")
            text = msg.get("text") or msg.get("content") or ""
            context += f"{role}: {text}\n"

    # Формируем промпт
    full_prompt = ""
    if context:
        full_prompt += f"История диалога:\n{context}\n"
    
    full_prompt += f"Вопрос пользователя: {question}"

    # Отправляем ИИ
    try:
        # Передаем device_type, если он есть, чтобы ИИ знал контекст
        answer = _ask_ai(full_prompt, device_type=device_type)
    except Exception as e:
        print(f"Ошибка в чате: {e}")
        answer = "Прошу прощения, сейчас я не могу связаться с сервером. Попробуйте позже."

    # Возвращаем JSON
    if "application/json" in ct:
        return {"answer": answer}
    
    # Возвращаем HTML (для тестов в браузере)
    return HTMLResponse(content=f"<html><body><h3>Ответ:</h3><p>{answer}</p></body></html>")

@app.get("/", include_in_schema=False)
def read_index():
    # Force update 2
    return FileResponse("static/index.html")

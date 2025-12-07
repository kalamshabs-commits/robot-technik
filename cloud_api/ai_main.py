import importlib, sys, os
sys.path.insert(0, os.path.dirname(__file__))

# Пытаемся подгрузить старые модули
for m in ("diagnostic_engine", "image_ai", "recall_parser"):
    try:
        importlib.import_module(m)
    except Exception:
        pass

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import pathlib
import requests
import io  
from PIL import Image
from .security import apply_security
from ai_helper import ask_ai as _ask_ai # Импорт функции общения с ИИ

app = FastAPI()
apply_security(app)

@app.get("/health")
def health():
    return {"status": "ok"}

# Подключаем статику
app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "static"), html=True), name="static")

# --- МОДЕЛЬ (YOLO) ---
_yolo_model = None
_model_dir = os.path.join(os.path.dirname(__file__), "..", "models")

async def _ensure_model():
    # Создаем папку если нет
    pathlib.Path(_model_dir).mkdir(parents=True, exist_ok=True)
    
    # 1. Пробуем найти best.pt (Твои веса)
    my_weights = os.path.join(_model_dir, "best.pt")
    default_weights = os.path.join(_model_dir, "yolov8n.pt")
    
    final_path = default_weights # По умолчанию
    
    if os.path.exists(my_weights):
        print(f"✅ Нашел твои веса: {my_weights}")
        final_path = my_weights
    elif not os.path.exists(default_weights):
        print("⚠ Весов нет, качаю стандартные...")
        try:
            url = "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"
            r = requests.get(url)
            with open(default_weights, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print(f"Ошибка скачивания: {e}")

    os.environ["YOLO_WEIGHTS_PATH"] = final_path

def _get_yolo():
    global _yolo_model
    if _yolo_model:
        return _yolo_model
    
    from ultralytics import YOLO
    path = os.environ.get("YOLO_WEIGHTS_PATH", "yolov8n.pt")
    print(f"🚀 Загружаю YOLO из: {path}")
    try:
        _yolo_model = YOLO(path)
    except Exception as e:
        print(f"Ошибка загрузки YOLO: {e}")
        _yolo_model = YOLO("yolov8n.pt") # Аварийный вариант
    return _yolo_model

# --- ДИАГНОСТИКА ---
@app.post("/ai/classify")
async def classify(file: UploadFile = File(...)):
    await _ensure_model()
    model = _get_yolo()
    
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return {"error": "Файл не картинка"}
    
    # Распознаем
    results = model.predict(source=img, conf=0.25, verbose=False)
    
    found_name = None
    max_conf = 0.0
    
    # Ищем самый четкий объект
    for box in results[0].boxes:
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        name = model.names[cls_id]
        if conf > max_conf:
            max_conf = conf
            found_name = name

    checklist = []
    
    if found_name:
        # ОБРАЩЕНИЕ К ИИ (DEEPSEEK)
        try:
            prompt = f"Я сфотографировал прибор: {found_name}. Напиши краткий чек-лист (3 пункта) для диагностики неисправностей. Только пункты."
            ai_text = _ask_ai(prompt, device_type=found_name)
            # Чистим текст в список
            checklist = [line.strip("- *") for line in ai_text.split('\n') if len(line) > 5]
        except Exception:
            checklist = [f"Прибор: {found_name}. Проверьте шнур питания.", "Осмотрите корпус."]
    else:
        found_name = "Не распознано"
        checklist = ["Попробуйте сделать фото четче или ближе."]

    return {
        "summary": f"Результат: {found_name}",
        "diagnosisChecklist": checklist,
        "repairChecklist": [],
        "suspectNodes": [],
        "timeEstimateMinutes": {"min": 10, "max": 20},
        "risks": [],
        "classes": []
    }

# --- ЧАТ ---
@app.post("/ai/ask")
async def ask(request: Request):
    try:
        data = await request.json()
    except:
        form = await request.form()
        data = dict(form)
        
    question = data.get("question", "")
    # ВАЖНО: Мы больше не требуем device_type жестко
    
    if not question:
        return {"answer": "Спроси меня о чем-нибудь!"}

    # Сразу идем к ИИ
    answer = _ask_ai(question)
    return {"answer": answer}

@app.get("/", include_in_schema=False)
def read_index():
    return FileResponse("static/index.html") 
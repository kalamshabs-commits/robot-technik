import os
import io
import sys
import traceback # Добавили для отлова ошибок
from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from PIL import Image

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# --- ВАЖНО: Разрешаем загрузку больших фото (16 МБ) ---
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

_model_ready = False
_model_dir = os.path.join(os.path.dirname(__file__), "models")
_yolo_model = None

def _get_weights_path():
    env_path = os.environ.get("YOLO_WEIGHTS_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    candidates = [
        os.path.join(_model_dir, "best.pt"),
        os.path.join(_model_dir, "yolov8n.pt"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def _ensure_model():
    global _model_ready
    if _model_ready:
        return
    wp = _get_weights_path()
    if not wp:
        print("WARNING: Веса модели не найдены!")
    else:
        os.environ["YOLO_WEIGHTS_PATH"] = wp
    _model_ready = True

def _ensure_yolo_model():
    global _yolo_model
    if _yolo_model is not None:
        return
    try:
        from ultralytics import YOLO
        wp = _get_weights_path()
        if not wp:
            return # Работаем без модели, если её нет
        _yolo_model = YOLO(wp)
    except Exception as e:
        print(f"Error loading YOLO: {e}")

# --- РОУТЫ ---

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)

@app.route("/manifest.json")
def manifest():
    # Важно: Чтобы браузер точно видел манифест
    return send_from_directory(app.static_folder, "manifest.json", mimetype='application/manifest+json')

@app.route("/sw.js")
def sw():
    return send_from_directory(app.static_folder, "sw.js")

@app.route("/ai/chat", methods=["POST"]) 
def ai_chat():
    try:
        ct = request.headers.get("Content-Type", "")
        payload = request.get_json(silent=True) if "application/json" in ct else request.form.to_dict() 
        q = (payload or {}).get("question") or ""
        dt = (payload or {}).get("device_type") or ""
        
        if not q.strip():
            return jsonify({"answer": "Напишите вопрос."})

        # Импортируем помощника
        from ai_helper import ask_ai as _ask_ai
        
        # Запрашиваем ответ
        ans = _ask_ai(q, device_type=dt)
        return jsonify({"answer": ans})

    except Exception as e:
        # ВЫВОДИМ РЕАЛЬНУЮ ОШИБКУ В ОТВЕТ (для отладки)
        print("AI ERROR:", e)
        traceback.print_exc() # Пишет ошибку в логи Google Cloud
        return jsonify({"answer": f"Ошибка сервера: {str(e)}"})

@app.route("/ai/classify", methods=["POST"]) 
def ai_classify():
    try:
        _ensure_model()
        _ensure_yolo_model()
        f = request.files.get("file")
        if not f:
            return jsonify({"error": "Нет файла"}), 400
        
        data = f.read()
        img = Image.open(io.BytesIO(data)).convert("RGB")
        
        # Если модель загрузилась - используем, если нет - заглушка
        main_name = ""
        if _yolo_model:
            res = _yolo_model.predict(source=img, verbose=False)
            # (Упрощенная логика получения первого класса)
            if res[0].boxes:
                c = int(res[0].boxes.cls[0])
                names = _yolo_model.names
                main_name = names[c] if c in names else str(c)

        mapping = {
            "printer": "printer",
            "smartphone": "smartphone",
            "laptop": "laptop",
            "microwave": "microwave",
            "breadmaker": "breadmaker",
            "multicooker": "multicooker"
        }
        # Нормализация имени
        fault_key = mapping.get((main_name or "").lower(), "")
        if not fault_key and main_name: fault_key = main_name # Если не нашли в маппинге, отдаем как есть

        return jsonify({
            "fault": fault_key,
            "checklist": [main_name] if main_name else []
        })

    except Exception as e:
        print("CLASSIFY ERROR:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route("/knowledge")
def knowledge():
    path = os.path.join(os.path.dirname(__file__), "faults_library.json")
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception:
        return jsonify({}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))

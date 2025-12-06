import os
import json
from flask import Flask, request, jsonify, render_template, send_from_directory
from ultralytics import YOLO
from PIL import Image
import io
# Импортируем твой помощник ИИ
from ai_helper import ask_ai

app = Flask(__name__)

# --- 1. ЗАГРУЗКА МОДЕЛИ YOLO (Диагностика) ---
try:
    # Ищем модель везде, чтобы не было ошибки
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(BASE_DIR, "models", "best.pt")
    
    if not os.path.exists(model_path):
        print(f"⚠️ Модель не найдена в {model_path}, ищу в корне...")
        model_path = "best.pt"

    print(f"🚀 Загружаю модель из: {model_path}")
    model = YOLO(model_path)
except Exception as e:
    print(f"❌ Ошибка загрузки модели: {e}")
    # Если своей модели нет, грузим стандартную, чтобы сайт не упал
    model = YOLO("yolov8n.pt")

# --- 2. ГЛАВНАЯ СТРАНИЦА ---
@app.route('/')
def home():
    return render_template('index.html')

# --- 3. РАБОТА С PWA ФАЙЛАМИ ---
@app.route('/manifest.json')
def manifest():
    return send_from_directory('static', 'manifest.json')

@app.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

# --- 4. ДИАГНОСТИКА (КЛАССИФИКАЦИЯ) ---
@app.route('/ai/classify', methods=['POST'])
def classify_image():
    if 'file' not in request.files:
        return jsonify({"error": "Нет файла"}), 400
    
    file = request.files['file']
    try:
        # Читаем картинку
        img_bytes = file.read()
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        
        # Прогоняем через YOLO
        results = model(img)
        
        # Берем первый результат
        r = results[0]
        
        detected_name = ""
        # Смотрим, что нашла нейросеть
        if r.boxes and len(r.boxes) > 0:
            cls_id = int(r.boxes.cls[0])
            detected_name = model.names[cls_id]
        
        return jsonify({
            "status": "ok", 
            "fault": detected_name  # Например: "printer", "laptop"
        })
        
    except Exception as e:
        print(f"Ошибка классификации: {e}")
        return jsonify({"error": str(e)}), 500

# --- 5. ЧАТ С ИИ И ЧЕК-ЛИСТЫ ---
@app.route('/ai/chat', methods=['POST'])
def chat_endpoint():
    data = request.json
    user_question = data.get('question', '')
    device_type = data.get('device_type', None)
    
    # Спрашиваем функцию из твоего файла ai_helper.py
    answer = ask_ai(user_question, device_type)
    
    return jsonify({"answer": answer})

# --- 6. БАЗА ЗНАНИЙ (JSON) ---
@app.route('/knowledge')
def get_knowledge():
    try:
        with open('faults_library.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

if __name__ == '__main__':
    # Для локального запуска
    app.run(host='0.0.0.0', port=8080)
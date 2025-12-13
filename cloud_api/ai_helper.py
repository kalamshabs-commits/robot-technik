import os
import json
import io
import logging
from PIL import Image
from ultralytics import YOLO
from openai import OpenAI
from typing import List, Dict, Optional, Tuple

# --- ИСПРАВЛЕНИЕ: НАСТРОЙКА ЛОГГЕРА ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
client = OpenAI(
    api_key="sk-fa49380289024753a4596a2c25dae955", # Твой ключ
    base_url="https://api.deepseek.com"
)
MODEL_NAME = "deepseek-chat"

# --- 2. ЧЕСТНЫЙ СЛОВАРЬ (Только твои классы) ---
YOLO_CLASSES_RU = {
    'multicooker': 'Мультиварка',
    'smartphone': 'Смартфон',
    'laptop': 'Ноутбук',
    'printer': 'Принтер',
    'microwave': 'Микроволновка',
    'breadmaker': 'Хлебопечка'
}

# --- DATABASE LOADING ---
def _load_faults_db() -> Dict:
    """
    Robustly attempts to load faults_library.json from multiple possible locations.
    """
    possible_paths = [
        "faults_library.json", # Current dir
        os.path.join(os.path.dirname(__file__), "faults_library.json"), # Same dir as this file
        os.path.join(os.path.dirname(__file__), "..", "faults_library.json"), # Parent dir
        "/app/faults_library.json", # Docker root
        "../faults_library.json" # One level up
    ]
    
    for path in possible_paths:
        try:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                logger.info(f"✅ Loading DB from: {abs_path}")
                with open(abs_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Error reading {path}: {e}")
            continue
            
    logger.error("❌ Critical: faults_library.json not found!")
    return {}

FAULTS_DB = _load_faults_db()

# --- MODEL LOADING ---
def get_model():
    # Ищем best.pt везде, где он может быть
    possible_paths = [
        "models/best.pt",
        "../models/best.pt",
        "./best.pt",
        "/app/models/best.pt"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                logger.info(f"✅ Загружаю ТВОИ веса из: {path}")
                return YOLO(path)
            except Exception as e:
                logger.error(f"Ошибка загрузки {path}: {e}")
    
    logger.error("❌ КРИТИЧНО: Файл best.pt не найден! Распознавание не сработает.")
    return None

MODEL = get_model()

# --- 4. АНАЛИЗ ФОТО ---
def analyze_image(image_bytes):
    if not MODEL:
        return None, 0.0
        
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Запускаем распознавание с порогом 15%
        results = MODEL.predict(source=img, conf=0.15, verbose=False)
        
        if not results:
            return None, 0.0

        # ПЕРЕБИРАЕМ ВСЕ НАЙДЕННЫЕ ОБЪЕКТЫ
        best_name = None
        best_conf = 0.0

        for r in results:
            if hasattr(r, 'boxes'):
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    eng_name = MODEL.names[cls_id] 
                    conf = float(box.conf[0])
                    
                    logger.info(f"YOLO увидела: {eng_name} ({conf:.2f})")

                    if eng_name in YOLO_CLASSES_RU:
                        if conf > best_conf:
                            best_conf = conf
                            best_name = YOLO_CLASSES_RU[eng_name]
        
        if best_name:
            return best_name, best_conf
        
        return None, 0.0
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа: {e}")
        return None, 0.0

# --- 5. ЧАТ С ИИ ---
def ask_ai(user_text, device_type=None, kb_info=None):
    if not client:
        return "Ошибка: API ключ не настроен."

    try:
        system_role = (
            "Ты профессиональный мастер по ремонту. Твой язык Русский. "
            "Если пользователь просто здоровается — отвечай кратко и вежливо. "
            "Если описывает проблему — отвечай как эксперт (Диагноз, Причина, Решение). "
            "Будь краток и точен. "
            "Если тебя просят чек-лист, давай нумерованный список."
        )
        
        user_content = user_text
        if device_type:
            user_content = (
                f"Устройство: {device_type}. "
                f"Проблема/Симптомы: {user_text}. "
            )
            if kb_info:
                user_content += f"\nИз базы знаний есть такая информация: {kb_info}."
            
            user_content += (
                "\nСоставь подробный план ремонта, используя и базу (если есть), и свои общие знания. "
                "Ответ должен быть единым, связным текстом (чек-листом)."
            )
            
        # DeepSeek call
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": user_content},
            ],
            stream=False
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"DeepSeek Error: {e}")
        return "Сервис ИИ временно недоступен."
 
    
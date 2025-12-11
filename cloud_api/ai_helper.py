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
    'breadmaker': 'Хлебопечка',
    # Добавь сюда другие, если твоя модель их знает (например, kettle, iron)
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
                print(f"✅ Loading DB from: {abs_path}")
                with open(abs_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading {path}: {e}")
            continue
            
    print("❌ Critical: faults_library.json not found!")
    return {}

FAULTS_DB = _load_faults_db()

# --- MODEL LOADING ---
def _load_model():
    # Ищем best.pt везде, где он может быть
    current_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(current_dir, "best.pt"),
        os.path.join(current_dir, "..", "best.pt"),
        "best.pt",
        os.path.join(os.path.dirname(__file__), "best.pt"),
        os.path.join(os.path.dirname(__file__), "..", "best.pt"),
        "/app/best.pt",
        "../best.pt"
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

MODEL = _load_model()

# --- 4. АНАЛИЗ ФОТО ---
def analyze_image(image_bytes):
    if not MODEL:
        return None, 0.0
        
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        
        # Запускаем распознавание с порогом 15%
        # (достаточно низкий, чтобы увидеть, но отсеять мусор)
        results = MODEL.predict(source=img, conf=0.15, verbose=False)
        
        if not results:
            return None, 0.0

        # ПЕРЕБИРАЕМ ВСЕ НАЙДЕННЫЕ ОБЪЕКТЫ
        for r in results:
            if hasattr(r, 'boxes'):
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    # Получаем имя класса из модели (например, 'laptop')
                    eng_name = MODEL.names[cls_id] 
                    conf = float(box.conf[0])
                    
                    logger.info(f"YOLO увидела: {eng_name} ({conf:.2f})")

                    # Если этот класс есть в нашем списке — возвращаем перевод
                    if eng_name in YOLO_CLASSES_RU:
                        return YOLO_CLASSES_RU[eng_name], conf
        
        # Если ничего из нашего списка не нашли
        return None, 0.0
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа: {e}")
        return None, 0.0

# --- 5. ЧАТ С ИИ ---
# ИСПРАВЛЕНИЕ: Добавили context_text=None в скобки 👇
def ask_ai(user_text, device_type=None, kb_info=None, context_text=None):
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
        
        # Теперь эта строчка сработает, потому что мы объявили переменную выше
        if context_text:
            system_role += f"\nИспользуй эту информацию из документа: {context_text[:2000]}..." # Limit context size
        
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
    
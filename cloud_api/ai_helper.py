import os
import json
import io
from PIL import Image
from ultralytics import YOLO
from openai import OpenAI
from typing import List, Dict, Optional, Tuple

# --- CONFIGURATION ---
client = OpenAI(
    api_key="sk-fa49380289024753a4596a2c25dae955",
    base_url="https://api.deepseek.com"
)
MODEL_NAME = "deepseek-chat"

# --- TRANSLATION DICTIONARY ---
YOLO_CLASSES_RU = {
    'cell phone': 'Смартфон', 'remote': 'Смартфон',
    'laptop': 'Ноутбук', 'tv': 'Ноутбук',
    'printer': 'Принтер', 'mouse': 'Принтер',
    'toaster': 'Хлебопечка',
    'microwave': 'Микроволновка',
    'oven': 'Мультиварка', 'bowl': 'Мультиварка', 'pot': 'Мультиварка'
}

ALLOWED_DEVICES = {
    "multicooker", "smartphone", "laptop", 
    "printer", "microwave", "breadmaker"
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
    possible_paths = [
        "best.pt",
        os.path.join(os.path.dirname(__file__), "best.pt"),
        os.path.join(os.path.dirname(__file__), "..", "best.pt"),
        "/app/best.pt",
        "../best.pt"
    ]
    
    for path in possible_paths:
        try:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                print(f"✅ Loading Model from: {abs_path}")
                return YOLO(abs_path)
        except Exception as e:
            print(f"⚠️ Error loading model from {path}: {e}")
            continue
    
    print("❌ Critical: best.pt not found! YOLO disabled.")
    return None

MODEL = _load_model()

def analyze_image(image_bytes: bytes) -> Tuple[Optional[str], float]:
    if not MODEL:
        return None, 0.0
        
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Lower confidence threshold to 0.1 as requested
        results = MODEL(img, conf=0.1)
        
        # Parse results
        if not results or not results[0].boxes:
            return None, 0.0
            
        box = results[0].boxes[0]
        cls_id = int(box.cls)
        conf = float(box.conf)
        name = results[0].names[cls_id]
        
        # Only return if it's in our allowed list
        if name not in YOLO_CLASSES_RU:
             return None, 0.0

        return name, conf
        
    except Exception as e:
        print(f"❌ Image Analysis Error: {e}")
        return None, 0.0

# --- HELPER FUNCTIONS ---
def _detect_device_rule_based(text: str) -> str:
    """
    Simple rule-based detection to avoid calling AI for everything.
    """
    text = text.lower()
    rules = {
        "printer": ["принтер", "печать", "мфу", "замял", "картридж"],
        "multicooker": ["мультивар", "суп", "каша", "рис", "пар"],
        "laptop": ["ноутбук", "лэптоп", "экран", "клавиатура", "зарядка"],
        "smartphone": ["смартфон", "телефон", "андроид", "айфон", "экран"],
        "microwave": ["микроволн", "свч", "греет", "искрит", "тарелка"],
        "breadmaker": ["хлебопеч", "хлеб", "тесто", "замес"]
    }
    
    for device, keywords in rules.items():
        for kw in keywords:
            if kw in text:
                return device
    return ""

def get_local_solution(device: str, query: str) -> Optional[str]:
    """
    Tries to find a solution in the local JSON DB.
    """
    if device not in FAULTS_DB:
        return None
        
    common_faults = FAULTS_DB[device].get("common_faults", [])
    query_lower = query.lower()
    
    # 1. Exact match in title
    for fault in common_faults:
        if fault["title"].lower() in query_lower:
            return f"**{fault['title']}**\n\n{fault['solution']}"
            
    # 2. Keyword match
    for fault in common_faults:
        keywords = fault.get("symptom_keywords", [])
        for kw in keywords:
            if kw.lower() in query_lower:
                return f"**{fault['title']}**\n\n{fault['solution']}"
                
    return None

# --- AI CLIENT ---
def ask_ai(user_text: str, device_type: str = None, kb_info: str = None, context_text: str = None) -> str:
    """
    Main entry point for AI advice.
    Hybrid Logic:
    1. Try rule-based device detection if not provided.
    2. DeepSeek API with KB info context.
    3. Fallback to local DB if API fails.
    """
    
    # 1. Normalize device type
    if not device_type:
        device_type = _detect_device_rule_based(user_text)
    
    # 2. Ask DeepSeek (Hybrid)
    try:
        system_role = (
            "Ты профессиональный мастер по ремонту. Твой язык Русский. "
            "Если пользователь просто здоровается — отвечай кратко и вежливо. "
            "Если описывает проблему — отвечай как эксперт (Диагноз, Причина, Решение). "
            "Будь краток и точен. "
            "Если тебя просят чек-лист, давай нумерованный список."
        )
        
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
        print(f"❌ DeepSeek API Error: {e}")
        return f"SYSTEM ERROR: {str(e)}"
        
        # Fallback Logic
        if kb_info:
             return f"**Режим оффлайн (База знаний):**\n\n{kb_info}\n\n(Сервис ИИ временно недоступен)"
        
        if device_type:
             local_res = get_local_solution(device_type, user_text)
             if local_res:
                 return f"**Режим оффлайн (База знаний):**\n\n{local_res}\n\n(Сервис ИИ временно недоступен)"
        
        return "Сервис перегружен, проверьте базовые настройки питания."

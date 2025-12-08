import os
import json
import io
from PIL import Image
from ultralytics import YOLO
import google.generativeai as genai
from typing import List, Dict, Optional, Tuple

# --- CONFIGURATION ---
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL_NAME = "gemini-1.5-flash"

# --- TRANSLATION DICTIONARY ---
YOLO_CLASSES_RU = {
    "person": "Человек",
    "bicycle": "Велосипед",
    "car": "Автомобиль",
    "motorcycle": "Мотоцикл",
    "airplane": "Самолет",
    "bus": "Автобус",
    "train": "Поезд",
    "truck": "Грузовик",
    "boat": "Лодка",
    "traffic light": "Светофор",
    "fire hydrant": "Пожарный гидрант",
    "stop sign": "Знак СТОП",
    "parking meter": "Паркомат",
    "bench": "Скамейка",
    "bird": "Птица",
    "cat": "Кошка",
    "dog": "Собака",
    "horse": "Лошадь",
    "sheep": "Овца",
    "cow": "Корова",
    "elephant": "Слон",
    "bear": "Медведь",
    "zebra": "Зебра",
    "giraffe": "Жираф",
    "backpack": "Рюкзак",
    "umbrella": "Зонт",
    "handbag": "Сумка",
    "tie": "Галстук",
    "suitcase": "Чемодан",
    "frisbee": "Фрисби",
    "skis": "Лыжи",
    "snowboard": "Сноуборд",
    "sports ball": "Мяч",
    "kite": "Воздушный змей",
    "baseball bat": "Бейсбольная бита",
    "baseball glove": "Бейсбольная перчатка",
    "skateboard": "Скейтборд",
    "surfboard": "Доска для серфинга",
    "tennis racket": "Теннисная ракетка",
    "bottle": "Бутылка",
    "wine glass": "Бокал",
    "cup": "Чашка",
    "fork": "Вилка",
    "knife": "Нож",
    "spoon": "Ложка",
    "bowl": "Миска",
    "banana": "Банан",
    "apple": "Яблоко",
    "sandwich": "Сэндвич",
    "orange": "Апельсин",
    "broccoli": "Брокколи",
    "carrot": "Морковь",
    "hot dog": "Хот-дог",
    "pizza": "Пицца",
    "donut": "Пончик",
    "cake": "Торт",
    "chair": "Стул",
    "couch": "Диван",
    "potted plant": "Цветок в горшке",
    "bed": "Кровать",
    "dining table": "Стол",
    "toilet": "Туалет",
    "tv": "Монитор / Экран",
    "tvmonitor": "Монитор",
    "laptop": "Ноутбук",
    "mouse": "Мышь",
    "remote": "Пульт",
    "keyboard": "Клавиатура",
    "cell phone": "Смартфон",
    "microwave": "Микроволновка",
    "oven": "Духовка / Хлебопечка",
    "toaster": "Тостер / Мультиварка",
    "sink": "Раковина",
    "refrigerator": "Холодильник",
    "book": "Книга",
    "clock": "Часы",
    "vase": "Ваза",
    "scissors": "Ножницы",
    "teddy bear": "Плюшевый мишка",
    "hair drier": "Фен",
    "toothbrush": "Зубная щетка",
    "printer": "Принтер",
    # Specific Appliances (mapped to YOLO classes or custom logic)
    "multicooker": "Мультиварка",
    "breadmaker": "Хлебопечка",
    "washer": "Стиральная машина",
    "dryer": "Сушильная машина",
    "dishwasher": "Посудомойка",
    "heater": "Обогреватель",
    "air conditioner": "Кондиционер",
    "fan": "Вентилятор",
    "vacuum": "Пылесос",
    "iron": "Утюг",
    "kettle": "Чайник",
    "blender": "Блендер",
    "mixer": "Миксер",
    "coffee maker": "Кофеварка"
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
        # Lower confidence threshold to 0.10 as requested
        results = MODEL(img, conf=0.1)
        
        # Parse results
        if not results or not results[0].boxes:
            return None, 0.0
            
        box = results[0].boxes[0]
        cls_id = int(box.cls)
        conf = float(box.conf)
        name = results[0].names[cls_id]
        
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
def ask_ai(user_text: str, device_type: str = None, kb_info: str = None) -> str:
    """
    Main entry point for AI advice.
    Hybrid Logic:
    1. Try rule-based device detection if not provided.
    2. Google Gemini API with KB info context.
    3. Fallback to local DB if API fails.
    """
    
    # 1. Normalize device type
    if not device_type:
        device_type = _detect_device_rule_based(user_text)
    
    # 2. Ask Gemini (Hybrid)
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        
        system_role = (
            "Ты профессиональный мастер по ремонту. Твой язык Русский. Будь краток и точен. "
            "Давай четкие, пошаговые инструкции. "
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
            
        # Gemini call
        prompt = f"{system_role}\n\n{user_content}"
        response = model.generate_content(prompt)
        
        return response.text
        
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")
        return f"SYSTEM ERROR: {str(e)}"
        
        # Fallback Logic
        if kb_info:
             return f"**Режим оффлайн (База знаний):**\n\n{kb_info}\n\n(Сервис ИИ временно недоступен)"
        
        if device_type:
             local_res = get_local_solution(device_type, user_text)
             if local_res:
                 return f"**Режим оффлайн (База знаний):**\n\n{local_res}\n\n(Сервис ИИ временно недоступен)"
        
        return "Сервис перегружен, проверьте базовые настройки питания."

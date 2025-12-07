import os
import json
import io
from PIL import Image
from ultralytics import YOLO
from openai import OpenAI
from typing import List, Dict, Optional, Tuple

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-fa49380289024753a4596a2c25dae955")
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

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
    "tv": "Телевизор",
    "tvmonitor": "Монитор",
    "laptop": "Ноутбук",
    "mouse": "Мышь",
    "remote": "Пульт ДУ",
    "keyboard": "Клавиатура",
    "cell phone": "Смартфон",
    "microwave": "Микроволновка",
    "oven": "Духовка",
    "toaster": "Тостер",
    "sink": "Раковина",
    "refrigerator": "Холодильник",
    "book": "Книга",
    "clock": "Часы",
    "vase": "Ваза",
    "scissors": "Ножницы",
    "teddy bear": "Плюшевый мишка",
    "hair drier": "Фен",
    "toothbrush": "Зубная щетка",
    # Specific Appliances (if model detects them)
    "multicooker": "Мультиварка",
    "breadmaker": "Хлебопечка",
    "printer": "Принтер",
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
        results = MODEL(img)
        
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
def _get_ai_client():
    try:
        return OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL, timeout=30.0)
    except Exception as e:
        print(f"❌ AI Client Init Error: {e}")
        return None

def ask_ai(user_text: str, device_type: str = None, kb_info: str = None) -> str:
    """
    Main entry point for AI advice.
    Hybrid Logic:
    1. Try rule-based device detection if not provided.
    2. DeepSeek API with KB info context.
    """
    
    # 1. Normalize device type
    if not device_type:
        device_type = _detect_device_rule_based(user_text)
    
    # 2. Ask DeepSeek (Hybrid)
    client = _get_ai_client()
    if not client:
        return "Ошибка: Не могу подключиться к мозгу ИИ (Нет клиента)."

    try:
        system_prompt = (
            "Ты — профессиональный мастер по ремонту техники 'Робот-техник'. "
            "Твоя задача — давать четкие, пошаговые инструкции по диагностике и ремонту. "
            "Если вопрос не касается ремонта, поддерживай вежливую беседу. "
            "Отвечай на русском языке. Используй форматирование (списки, жирный текст). "
            "Если тебя просят чек-лист, давай нумерованный список. Будь краток и по делу."
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
                "Если информация из базы полезна, обязательно включи её. "
                "Ответ должен быть единым, связным текстом (чек-листом)."
            )

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ DeepSeek API Error: {error_str}")
        if "402" in error_str or "Insufficient Balance" in error_str:
             return "К сожалению, баланс ИИ исчерпан. Попробуйте позже."
             
        return f"Произошла ошибка при связи с ИИ. Попробуйте позже. (Код ошибки: {error_str})"

import os
import json
from openai import OpenAI
from typing import List, Dict, Optional

# --- CONFIGURATION ---
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-fa49380289024753a4596a2c25dae955")
BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

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
            if os.path.exists(path):
                print(f"✅ Loading DB from: {path}")
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading {path}: {e}")
            continue
            
    print("❌ Critical: faults_library.json not found!")
    return {}

FAULTS_DB = _load_faults_db()

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

def _get_local_solution(device: str, query: str) -> Optional[str]:
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

def ask_ai(user_text: str, device_type: str = None) -> str:
    """
    Main entry point for AI advice.
    Hybrid Logic:
    1. Try rule-based device detection if not provided.
    2. Try local DB lookup (fast, offline-friendly).
    3. Fallback to DeepSeek API (slow, smart).
    """
    
    # 1. Normalize device type
    if not device_type:
        device_type = _detect_device_rule_based(user_text)
    
    # 2. Try Local DB
    if device_type:
        local_sol = _get_local_solution(device_type, user_text)
        if local_sol:
            print(f"✅ Found local solution for {device_type}")
            return f"[Из Базы Знаний]\n{local_sol}"

    # 3. Ask DeepSeek
    client = _get_ai_client()
    if not client:
        return "Ошибка: Не могу подключиться к мозгу ИИ (Нет клиента)."

    try:
        system_prompt = (
            "Ты — профессиональный мастер по ремонту техники 'Робот-техник'. "
            "Твоя задача — давать четкие, пошаговые инструкции по диагностике и ремонту. "
            "Отвечай на русском языке. Используй форматирование (списки, жирный текст). "
            "Если тебя просят чек-лист, давай нумерованный список. Будь краток и по делу."
        )
        
        user_content = user_text
        if device_type:
            user_content = (
                f"Устройство: {device_type}. "
                f"Проблема/Симптомы: {user_text}. "
                f"Составь пошаговый чек-лист (Checklist) для диагностики и устранения неисправностей."
            )

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        return response.choices[0].message.content
        
    except Exception as e:
        print(f"❌ DeepSeek API Error: {e}")
        return f"Произошла ошибка при связи с ИИ. Попробуйте позже. (Код ошибки: {str(e)})"

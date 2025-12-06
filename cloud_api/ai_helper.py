import os
import json
from openai import OpenAI

# ==========================================
# НАСТРОЙКИ (Берем из переменных Cloud Run)
# ==========================================
# Если ключа нет в настройках сервера, программа не упадет, а напишет None
API_KEY = os.getenv("OPENAI_API_KEY") 
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = "deepseek-chat"

# Инициализация клиента
client = None
if API_KEY:
    try:
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    except Exception as e:
        print(f"Ошибка инициализации OpenAI: {e}")

# --- Загрузка базы знаний ---
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(BASE_DIR, 'faults_library.json')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        FAULTS_DB = json.load(f)
except Exception as e:
    print(f"Ошибка загрузки базы знаний: {e}")
    FAULTS_DB = {}

def ask_ai(user_text, device_type=None):
    if not client:
        return "Ошибка: API ключ не найден. Проверьте настройки в Google Cloud (Variables)."

    try:
        # --- ШАГ 1: ЛОКАЛЬНАЯ БАЗА ---
        if device_type and device_type in FAULTS_DB:
            if "чек-лист" not in user_text.lower() and len(user_text) < 50:
                device_data = FAULTS_DB[device_type]
                for fault in device_data.get("common_faults", []):
                    if isinstance(fault, dict):
                        keywords = fault.get("symptom_keywords", [])
                        if any(word in user_text.lower() for word in keywords):
                            return f"<b>Быстрый ответ:</b><br>{fault.get('solution')}"

        # --- ШАГ 2: ЗАПРОС К ИИ ---
        system_msg = (
            "Ты — умный помощник по ремонту техники 'Робот-техник'. "
            "Твоя цель — помочь пользователю починить прибор. "
            "Отвечай на русском языке. Давай конкретные советы."
        )

        user_content = user_text
        if device_type:
            user_content = f"Устройство: {device_type}. Симптомы: {user_text}. Дай инструкцию по ремонту."

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7,
            max_tokens=1500
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Ошибка запроса к ИИ: {e}")
        return "Произошла ошибка связи с мозгом робота. Попробуйте позже."
import os
import json
from openai import OpenAI

# ==========================================
# НАСТРОЙКИ DEEPSEEK (Жесткая привязка)
# ==========================================
API_KEY = "sk-fa49380289024753a4596a2c25dae955"  # Ваш ключ
BASE_URL = "https://api.deepseek.com"          # Адрес DeepSeek
MODEL_NAME = "deepseek-chat"                   # Имя модели

# Инициализация клиента
try:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
except Exception as e:
    print(f"Ошибка настройки DeepSeek: {e}")
    client = None

# --- ИСПРАВЛЕНИЕ: Правильный путь к файлу в облаке ---
try:
    # Получаем папку, где лежит этот скрипт
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(BASE_DIR, 'faults_library.json')
    
    with open(json_path, 'r', encoding='utf-8') as f:
        FAULTS_DB = json.load(f)
except Exception as e:
    print(f"Ошибка загрузки базы знаний: {e}")
    FAULTS_DB = {}

def ask_ai(user_text, device_type=None):
    """
    Функция общения с ИИ.
    """
    if not client:
        return "Ошибка: Не настроен ключ API DeepSeek."

    try:
        # --- ШАГ 1: ЛОКАЛЬНАЯ БАЗА ---
        if device_type and device_type in FAULTS_DB:
            # Если вопрос короткий и не просят чек-лист - ищем в базе
            if "чек-лист" not in user_text.lower() and len(user_text) < 50:
                device_data = FAULTS_DB[device_type]
                for fault in device_data.get("common_faults", []):
                    # Проверка: если faults это список словарей
                    if isinstance(fault, dict):
                        keywords = fault.get("symptom_keywords", [])
                        if any(word in user_text.lower() for word in keywords):
                            return f"<b>Быстрый ответ:</b><br>{fault.get('solution')}"

        # --- ШАГ 2: ЗАПРОС К DEEPSEEK ---
        system_msg = (
            "Ты — умный помощник по ремонту техники 'Робот-техник'. "
            "Твоя цель — помочь пользователю починить прибор. "
            "Отвечай на русском языке. "
            "Используй HTML-теги для красоты: <b>жирный текст</b>, <br> новая строка. "
            "Если тебя просят решение проблемы, дай пошаговый чек-лист (список)."
        )

        user_content = user_text
        if device_type:
            user_content = f"Устройство: {device_type}. Симптомы: {user_text}. Напиши подробный чек-лист диагностики и ремонта."

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
        print(f"Ошибка DeepSeek: {e}")
        return f"Произошла ошибка связи с ИИ. Попробуйте позже. (Детали: {e})"

# Заглушки
def search_similar(img): return None
def _detect_device(text): return None
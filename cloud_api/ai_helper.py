import os
import json
from openai import OpenAI

# ==========================================
# НАСТРОЙКИ
# ==========================================
# ВНИМАНИЕ: Код теперь ищет переменную DEEPSEEK_API_KEY
# Убедись, что в Cloud Run переменная называется ТОЧНО ТАК ЖЕ
API_KEY = os.getenv("DEEPSEEK_API_KEY") 
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = "deepseek-chat"

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
except Exception:
    FAULTS_DB = {}

def ask_ai(user_text, device_type=None):
    if not client:
        return "Ошибка: Не найден API ключ. Проверьте переменную DEEPSEEK_API_KEY в Cloud Run."

    try:
        # --- ШАГ 1: БЫСТРЫЙ ОТВЕТ ИЗ БАЗЫ ---
        if device_type and device_type in FAULTS_DB:
            if len(user_text) < 50:
                device_data = FAULTS_DB[device_type]
                for fault in device_data.get("common_faults", []):
                    if isinstance(fault, dict):
                        keywords = fault.get("symptom_keywords", [])
                        if any(word in user_text.lower() for word in keywords):
                            return f"<b>Справочник:</b> {fault.get('solution')}"

        # --- ШАГ 2: ОБЩЕНИЕ С ИИ ---
        system_msg = (
            "Ты — 'Робот-техник', дружелюбный и умный ИИ-помощник. "
            "Твоя специализация — ремонт техники. "
            "Отвечай вежливо, кратко и по делу. "
            "Если вопрос касается ремонта, давай четкую инструкцию."
        )

        user_content = user_text
        if device_type:
            user_content = f"У меня устройство: {device_type}. Вопрос/Проблема: {user_text}. Помоги мне."

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"Ошибка AI: {e}")
        return "Мой мозг сейчас перегружен (ошибка связи). Спросите позже."
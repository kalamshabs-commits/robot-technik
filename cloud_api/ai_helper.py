import os
import json
from openai import OpenAI

# ==========================================
# ЧИСТЫЙ КОД ПОМОЩНИКА (ai_helper.py)
# ==========================================

# 1. Настройка ключа (Ищем DEEPSEEK_API_KEY, так как ты так назвала в Cloud Run)
API_KEY = os.getenv("DEEPSEEK_API_KEY") 
BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = "deepseek-chat"

client = None
if API_KEY:
    try:
        client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    except Exception as e:
        print(f"Ошибка инициализации OpenAI: {e}")
else:
    print("ВНИМАНИЕ: Ключ DEEPSEEK_API_KEY не найден. ИИ работать не будет.")

# 2. Загрузка базы знаний (faults_library.json)
FAULTS_DB = {}
try:
    # Ищем файл рядом с этим скриптом
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    # Проверяем в текущей папке и на папку выше (на всякий случай)
    paths = [
        os.path.join(cur_dir, 'faults_library.json'),
        os.path.join(cur_dir, '..', 'faults_library.json')
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, 'r', encoding='utf-8') as f:
                FAULTS_DB = json.load(f)
            break
except Exception as e:
    print(f"Ошибка загрузки базы знаний: {e}")

# 3. Главная функция общения
def ask_ai(user_text, device_type=None):
    # Если ключа нет - сразу говорим об этом
    if not client:
        return "Ошибка: Не найден API ключ (DEEPSEEK_API_KEY). Проверьте настройки сервера."

    try:
        # ШАГ А: Проверяем локальную базу (если вопрос короткий)
        if device_type and device_type in FAULTS_DB:
            if len(user_text) < 50: # Если вопрос короткий, ищем в справочнике
                device_data = FAULTS_DB[device_type]
                for fault in device_data.get("common_faults", []):
                    if isinstance(fault, dict):
                        keywords = fault.get("symptom_keywords", [])
                        if any(word in user_text.lower() for word in keywords):
                            return f"<b>Справочник:</b> {fault.get('solution')}"

        # ШАГ Б: Если в базе нет, идем к DeepSeek
        system_msg = (
            "Ты — 'Робот-техник', профессиональный помощник по ремонту. "
            "Твоя цель — помочь починить прибор. "
            "Отвечай вежливо, давай пошаговые инструкции. "
            "Если тебя спросили просто 'Привет' или отвлеченно — поддержи беседу."
        )

        user_content = user_text
        if device_type:
            user_content = f"Устройство: {device_type}. Проблема/Вопрос: {user_text}"

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
        print(f"Ошибка при запросе к ИИ: {e}")
        return "Извините, сейчас я не могу связаться с сервером (DeepSeek перегружен). Попробуйте позже."

# Этот блок нужен только для проверки на компьютере, на сервере он игнорируется
if __name__ == "__main__":
    print(ask_ai("Привет!"))
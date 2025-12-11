from ai_helper import ask_ai
import json

def diagnose(device, model, detected_objects):
    """
    Формирует словарь (report), который ожидает main.py для вывода на экран и PDF.
    """
    
    objects_str = ", ".join(detected_objects)
    
    # Промпт для ИИ, чтобы он вернул структуру, которую мы можем разобрать
    prompt = f"""
    Проведи диагностику: {device} (Модель: {model}).
    На фото я вижу детали: {objects_str}.
    
    Мне нужен ответ СТРОГО в формате JSON (без лишнего текста) с такими полями:
    {{
        "summary": "Краткая суть проблемы (1 предложение)",
        "risks": ["Риск 1", "Риск 2"],
        "steps": ["Шаг диагностики 1", "Шаг диагностики 2"],
        "repair": ["Шаг ремонта 1", "Шаг ремонта 2"],
        "tools": ["Инструмент 1", "Инструмент 2"],
        "min_time": 15,
        "max_time": 45
    }}
    """

    try:
        # 1. Спрашиваем ИИ
        response_text = ask_ai(prompt, device, model)
        
        # 2. Пытаемся найти JSON в ответе (ИИ может добавить ```json в начале)
        clean_json = response_text
        if "```json" in clean_json:
            clean_json = clean_json.split("```json")[1].split("```")[0]
        elif "```" in clean_json:
            clean_json = clean_json.split("```")[1].split("```")[0]
            
        data = json.loads(clean_json.strip())
        
        # 3. Собираем словарь точно под ваш main.py
        report = {
            "summary": data.get("summary", "Диагностика выполнена."),
            "risks": data.get("risks", []),
            # Превращаем строки в словари {"step": ...}, как хочет main.py
            "diagnosisChecklist": [{"step": s} for s in data.get("steps", [])],
            "repair_steps": data.get("repair", []),
            "tools_needed": data.get("tools", []),
            "timeEstimateMinutes": {
                "min": data.get("min_time", 10),
                "max": data.get("max_time", 60)
            }
        }
        return report

    except Exception:
        # Если ИИ вернул не JSON или произошла ошибка — возвращаем текстовый ответ как заглушку
        # Чтобы приложение не вылетело
        fallback_text = ask_ai(f"Дай краткую инструкцию по ремонту: {device}, вижу {objects_str}", device, model)
        return {
            "summary": "Автоматическая диагностика (текстовый режим)",
            "risks": ["Соблюдайте ТБ"],
            "diagnosisChecklist": [{"step": "Осмотрите устройство визуально"}],
            "repair_steps": [fallback_text], # Весь текст ответа кладем сюда
            "tools_needed": ["Набор инструментов"],
            "timeEstimateMinutes": {"min": 0, "max": 0}
        }
        
        
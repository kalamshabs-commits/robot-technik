import logging
import os
from ultralytics import YOLO

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_model = None

def get_yolo_model():
    global _model
    if _model:
        return _model
    
    # --- ИСПРАВЛЕНИЕ 1: АБСОЛЮТНЫЙ ПУТЬ ---
    # Получаем папку, где лежит этот скрипт (image_ai.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Ищем best.pt именно в этой папке
    model_path = os.path.join(current_dir, "best.pt")
    
    logger.info(f"🔍 Ищу модель по пути: {model_path}")
    
    if not os.path.exists(model_path):
        logger.error(f"❌ Файл {model_path} НЕ НАЙДЕН! Проверьте, загружен ли он в Git.")
        return None

    try:
        logger.info(f"🔍 Загружаю модель из: {model_path}")
        _model = YOLO(model_path)
        logger.info(f"🚀 Модель загружена успешно.")
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки YOLO: {e}")
        return None
        
    return _model

def recognize_objects(image_path):
    """
    Принимает путь к файлу (строку) и возвращает список объектов.
    """
    model = get_yolo_model()
    if not model:
        return ["Ошибка: нет модели"]

    try:
        logger.info(f"📸 Анализирую файл: {image_path}")

        # --- ИСПРАВЛЕНИЕ 2: СНИЖЕН ПОРОГ (conf=0.15) ---
        # Было 0.25, стало 0.15. Теперь она увидит даже смутные объекты.
        results = model.predict(source=image_path, conf=0.15, verbose=False)
        detected = []
        
        # Словарь перевода
        translations = {
            "multicooker": "Мультиварка",
            "laptop": "Ноутбук",
            "notebook": "Ноутбук", # На всякий случай
            "printer": "Принтер",
            "smartphone": "Смартфон",
            "phone": "Смартфон",
            "microwave": "Микроволновка",
            "breadmaker": "Хлебопечка",
            "kettle": "Чайник",
            "iron": "Утюг",
            "monitor": "Монитор",
            "screen": "Монитор",
            "oven": "Духовка",
            "washing machine": "Стиральная машина"
        }

        for r in results:
            # Проверка для детеции (boxes)
            if hasattr(r, 'boxes'):
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    name = model.names[cls_id]
                    # Переводим и добавляем (lower() для надежности)
                    ru_name = translations.get(name.lower(), name) 
                    detected.append(ru_name)
                    logger.info(f"   -> Найдено: {name} ({ru_name})")
            
            # Проверка для классификации (probs) - на случай если модель классификатор
            if hasattr(r, 'probs') and r.probs:
                top1 = r.probs.top1
                name = r.names[top1]
                ru_name = translations.get(name.lower(), name)
                detected.append(ru_name)

        # Возвращаем уникальные объекты
        if not detected:
            logger.warning("⚠️ Объекты не найдены (список пуст)")
            return ["Ничего не найдено"]

        return list(set(detected))
        
    except Exception as e:
        logger.error(f"🔥 Ошибка анализа фото: {e}")
        return ["Ошибка анализа"]
    
    
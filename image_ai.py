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
    
    # --- ИСПРАВЛЕНИЕ ПУТИ ---
    # Получаем папку, где лежит этот скрипт
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Сначала пробуем найти в папке models (это правильный вариант)
    model_path = os.path.join(current_dir, "models", "best.pt")
    
    # 2. Если там нет, пробуем искать рядом (на всякий случай)
    if not os.path.exists(model_path):
        logger.warning(f"⚠️ В папке models пусто. Ищу best.pt в корне...")
        model_path = os.path.join(current_dir, "best.pt")

    logger.info(f"🔍 Ищу модель по пути: {model_path}")
    
    # Если файла нигде нет - берем стандартную модель, чтобы сайт не упал
    if not os.path.exists(model_path):
        logger.error(f"❌ Файл best.pt НЕ НАЙДЕН! Загружаю стандартную yolov8n.pt")
        # Это спасет приложение от краша
        _model = YOLO("yolov8n.pt")
        return _model

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

        # Порог 0.15 - отлично для тестов
        results = model.predict(source=image_path, conf=0.15, verbose=False)
        detected = []
        
        # Словарь перевода (добавил 'cell phone' на всякий случай, это стандарт YOLO)
        translations = {
            "multicooker": "Мультиварка",
            "laptop": "Ноутбук",
            "notebook": "Ноутбук",
            "printer": "Принтер",
            "smartphone": "Смартфон",
            "phone": "Смартфон",
            "cell phone": "Смартфон",  # <-- Важно добавить!
            "mobile phone": "Смартфон",
            "microwave": "Микроволновка",
            "breadmaker": "Хлебопечка",
            "kettle": "Чайник",
            "iron": "Утюг",
            "monitor": "Монитор",
            "tv": "Монитор", # Часто путает с телевизором
            "screen": "Монитор",
            "oven": "Духовка",
            "washing machine": "Стиральная машина",
            "refrigerator": "Холодильник",
            "fridge": "Холодильник"
        }

        for r in results:
            # Детекция (boxes)
            if hasattr(r, 'boxes'):
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    name = model.names[cls_id]
                    # Переводим
                    ru_name = translations.get(name.lower(), name) 
                    detected.append(ru_name)
                    logger.info(f"   -> Найдено (box): {name} -> {ru_name}")
            
            # Классификация (probs)
            if hasattr(r, 'probs') and r.probs:
                try:
                    top1 = r.probs.top1
                    name = r.names[top1]
                    ru_name = translations.get(name.lower(), name)
                    detected.append(ru_name)
                    logger.info(f"   -> Найдено (prob): {name} -> {ru_name}")
                except:
                    pass

        # Если ничего не нашли
        if not detected:
            logger.warning("⚠️ Объекты не найдены (список пуст)")
            return ["Ничего не найдено"]

        return list(set(detected))
        
    except Exception as e:
        logger.error(f"🔥 Ошибка анализа фото: {e}")
        return ["Ошибка анализа"]
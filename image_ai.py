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
    
    # Ищем модель best.pt в текущей папке
    model_path = "best.pt"
    
    if not os.path.exists(model_path):
        logger.warning(f"⚠️ Файл {model_path} не найден! Будет ошибка при распознавании.")
        return None

    try:
        _model = YOLO(model_path)
        logger.info(f"🚀 Модель {model_path} загружена.")
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки YOLO: {e}")
        return None
        
    return _model

def recognize_objects(image_path):
    """
    Принимает путь к файлу (строку) от Kivy и возвращает список объектов.
    """
    model = get_yolo_model()
    if not model:
        return ["Ошибка: нет модели"]

    try:
        # Kivy передает путь к файлу, YOLO читает его сам
        results = model.predict(source=image_path, conf=0.25, verbose=False)
        detected = []
        
        # Словарь перевода (добавь сюда свои классы из обучения)
        translations = {
            "multicooker": "Мультиварка",
            "laptop": "Ноутбук",
            "printer": "Принтер",
            "smartphone": "Смартфон",
            "microwave": "Микроволновка",
            "breadmaker": "Хлебопечка",
            "kettle": "Чайник",
            "iron": "Утюг",
            "monitor": "Монитор"
        }

        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                name = model.names[cls_id]
                ru_name = translations.get(name, name) # Переводим
                detected.append(ru_name)
        
        # Возвращаем уникальные объекты
        return list(set(detected)) if detected else ["Ничего не найдено"]
        
    except Exception as e:
        logger.error(f"Ошибка анализа фото: {e}")
        return ["Ошибка анализа"]
    
    
# image_analyzer.py
import cv2

def analyze_image(path):
    try:
        img = cv2.imread(path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        dark_pixels = (gray < 40).sum()
        total_pixels = gray.size
        dark_ratio = dark_pixels / total_pixels

        notes = []
        if dark_ratio > 0.2:
            notes.append("Обнаружено потемнение — возможно, следы перегрева.")
        if dark_ratio > 0.5:
            notes.append("Сильное повреждение (обугливание).")

        return {"notes": "; ".join(notes)}
    except Exception as e:
        return {"notes": f"Ошибка анализа изображения: {e}"}

# robot_technician.py
import json
import cv2
from diagnostic_engine import diagnose
from image_analyzer import analyze_image

def main():
    print("🤖 Робот-техник — интеллектуальный помощник по диагностике\n")

    device_type = input("Введите тип устройства (принтер / ноутбук / другое): ").lower()
    description = input("Опишите неисправность: ")

    # Ввод измерений
    measurements = []
    while True:
        name = input("Введите название измерения (или Enter для пропуска): ")
        if not name:
            break
        value = input("Значение: ")
        unit = input("Единица измерения (В, Ом, °C и т.д.): ")
        measurements.append({"name": name, "value": value, "unit": unit})

    # Фото
    image_path = input("Укажите путь к фото (или Enter, если нет): ")
    image_analysis = None
    if image_path:
        image_analysis = analyze_image(image_path)

    # Диагностика
    report = diagnose(device_type, description, measurements, image_analysis)

    # Вывод отчёта
    print("\n📋 Результаты диагностики:")
    print("Резюме:", report["summary"])
    if report["risks"]:
        print("⚠️ Риски:", ", ".join(report["risks"]))
    print("\nЧек-лист диагностики:")
    for i, step in enumerate(report["diagnosisChecklist"], 1):
        print(f"{i}. {step['step']}")

    print("\nРекомендации по ремонту:")
    for i, step in enumerate(report["repairChecklist"], 1):
        print(f"{i}. {step['step']}")

    print("\nПодозрительные узлы:", ", ".join(report["suspectNodes"]))
    print("Оценка времени:", f"{report['timeEstimateMinutes']['min']}–{report['timeEstimateMinutes']['max']} мин.")

    # Сохранение отчёта
    with open("diagnostic_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("\n✅ Отчёт сохранён: diagnostic_report.json")

if __name__ == "__main__":
    main()

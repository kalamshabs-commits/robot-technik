import json
import os

ALLOWED = {"multicooker","smartphone","laptop","printer","microwave","breadmaker"}

def _load_faults():
    path = os.path.join(os.path.dirname(__file__), "faults_library.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _normalize_device(s):
    k = (s or '').strip().lower()
    if not k:
        return None
    if k in ALLOWED:
        return k
    if "принтер" in k or "печать" in k:
        return "printer"
    if "мультивар" in k or "суп" in k:
        return "multicooker"
    if "ноутбук" in k or "laptop" in k:
        return "laptop"
    if "смартфон" in k or "телефон" in k or "смарт" in k:
        return "smartphone"
    if "микровол" in k or "печь" in k:
        return "microwave"
    if "хлебопеч" in k or "хлеб" in k:
        return "breadmaker"
    return None

def _match_fault(items, text_or_list):
    text = text_or_list if isinstance(text_or_list, str) else " ".join(text_or_list or [])
    t = (text or '').lower()
    for f in items:
        kws = f.get("symptom_keywords") or []
        for kw in kws:
            if kw and str(kw).lower() in t:
                return f
    return items[0] if items else None

def diagnose(device_type, model_name, detected_objects, symptom_text=None):
    faults = _load_faults()
    dt = _normalize_device(device_type)
    if not dt:
        return {
            "summary": "Чиню только: multicooker, smartphone, laptop, printer, microwave, breadmaker",
            "diagnosisChecklist": [],
            "repairChecklist": [],
            "suspectNodes": [],
            "timeEstimateMinutes": {"min": 5, "max": 15},
            "risks": []
        }
    section = faults.get(dt) or {}
    items = section.get("common_faults") or []
    f = _match_fault(items, symptom_text or detected_objects)
    if not f:
        return {
            "summary": "Нет точного совпадения по симптомам",
            "diagnosisChecklist": [],
            "repairChecklist": [],
            "suspectNodes": [],
            "timeEstimateMinutes": {"min": 5, "max": 15},
            "risks": []
        }
    steps = [str(x) for x in (f.get("steps") or [])]
    return {
        "summary": f.get("title") or "Диагностика",
        "diagnosisChecklist": steps,
        "repairChecklist": steps,
        "suspectNodes": [{"class": dt, "confidence": 0.9, "bbox": None}],
        "timeEstimateMinutes": {"min": int(f.get("time_min") or 10), "max": int(f.get("time_max") or 30)},
        "risks": []
    }

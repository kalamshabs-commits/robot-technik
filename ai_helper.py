import os
import json
from typing import List, Dict
from diagnostic_engine import diagnose
from openai import OpenAI

ALLOWED = {"multicooker","smartphone","laptop","printer","microwave","breadmaker"}

def _load_faults():
    try:
        path = os.path.join(os.path.dirname(__file__), "faults_library.json")
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _detect_device(text: str) -> str:
    t = (text or '').lower()
    if "принтер" in t or "печать" in t:
        return "printer"
    if "мультивар" in t or "суп" in t:
        return "multicooker"
    if "ноутбук" in t or "laptop" in t:
        return "laptop"
    if "смартфон" in t or "телефон" in t or "смарт" in t:
        return "smartphone"
    if "микровол" in t or "печь" in t:
        return "microwave"
    if "хлебопеч" in t or "хлеб" in t:
        return "breadmaker"
    return ""

def _deepseek_client():
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        return None
    return OpenAI(base_url="https://api.deepseek.com", api_key=key, timeout=30.0)

def _find_fault(dt: str, title: str):
    data = _load_faults()
    items = (data.get(dt) or {}).get("common_faults") or []
    for f in items:
        if (f.get("title") or "").strip().lower() == (title or "").strip().lower():
            return f
    return None

def search_similar(query: str, device_type: str = "", top_k: int = 3) -> List[Dict]:
    data = _load_faults()
    dt = device_type or _detect_device(query)
    if not dt or dt not in ALLOWED:
        return []
    items = (data.get(dt) or {}).get("common_faults") or []
    out = []
    q = (query or '').lower()
    for f in items:
        kws = f.get("symptom_keywords") or []
        score = sum(1 for kw in kws if kw and str(kw).lower() in q)
        if score:
            out.append({"title": f.get("title"), "solution": f.get("solution"), "score": score})
    out.sort(key=lambda x: x.get("score", 0), reverse=True)
    return out[:top_k]

def ask_ai(prompt: str, device_type: str = "", model_name: str = "") -> str:
    dt = device_type or _detect_device(prompt)
    if dt and dt not in ALLOWED:
        return "Чиню только: multicooker, smartphone, laptop, printer, microwave, breadmaker"
    dt2 = dt or ""
    sims = search_similar(prompt, dt2, top_k=1)
    if sims:
        t = sims[0].get("title") or ""
        fault = _find_fault(dt2, t)
        steps = [str(x) for x in (fault or {}).get("steps", [])]
        if steps:
            return "\n".join(steps)
    client = _deepseek_client()
    if client:
        try:
            sys = "Ты — Робот-техник. Твоя задача — помогать чинить бытовую технику. Отвечай чеклистами. Будь краток."
            msgs = [
                {"role": "system", "content": sys},
                {"role": "user", "content": prompt},
            ]
            out = client.chat.completions.create(model="deepseek-chat", messages=msgs, temperature=0.2, max_tokens=500)
            return (out.choices[0].message.content or "").strip()
        except Exception:
            pass
    if not dt2:
        return "Уточните тип устройства из списка: мультиварка, смартфон, ноутбук, принтер, микроволновка, хлебопечка"
    report = diagnose(dt2, model_name or "", [], symptom_text=prompt)
    steps = report.get("diagnosisChecklist") or []
    if not steps:
        return "Нет точного совпадения по симптомам"
    return "\n".join([str(s) for s in steps])

import importlib, sys, os
sys.path.insert(0, os.path.dirname(__file__))
for m in ("diagnostic_engine", "image_ai", "recall_parser"):
    try:
        importlib.import_module(m)
    except Exception as e:
        print(f"{m} load fail:", e)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import tempfile
import os
import pathlib
import zipfile
import httpx
from PIL import Image, ImageDraw
import requests
import subprocess
import io
from .security import apply_security
from ai_helper import ask_ai as _ask_ai

app = FastAPI()
apply_security(app)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

app.mount("/", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "static"), html=True), name="static")

_model_ready = False
_model_dir = os.path.join(os.path.dirname(__file__), "..", "models")
_yolo_model = None
_icons_dir = os.path.join(os.path.dirname(__file__), "..", "static", "icons")

def _ensure_icons():
    try:
        os.makedirs(_icons_dir, exist_ok=True)
        for size in (192, 512):
            path = os.path.join(_icons_dir, f"icon-{size}.png")
            if os.path.exists(path):
                continue
            img = Image.new("RGBA", (size, size), "#FFFFFF")
            d = ImageDraw.Draw(img)
            c = "#2196F3"
            s = size
            w = max(2, s // 24)
            pad = s // 8
            screen = (pad, pad, s - pad, s // 2)
            d.rounded_rectangle(screen, radius=s // 24, outline=c, width=w)
            bh = s // 10
            d.rectangle((int(pad * 1.5), int(s // 2 + pad // 2), int(s - pad * 1.5), int(s // 2 + pad // 2 + bh)), outline=c, width=w)
            pw = s // 3
            ph = s // 4
            px = s // 2 - pw // 2
            py = s - pad - ph
            d.rounded_rectangle((px, py, px + pw, py + ph), radius=s // 32, outline=c, width=w)
            img.save(path, "PNG")
        final = os.path.join(_icons_dir, "icon-512-final.png")
        if not os.path.exists(final):
            size = 512
            img = Image.new("RGBA", (size, size), "#FFFFFF")
            d = ImageDraw.Draw(img)
            c = "#2196F3"
            s = size
            w = max(2, s // 24)
            pad = s // 8
            screen = (pad, pad, s - pad, s // 2)
            d.rounded_rectangle(screen, radius=s // 24, outline=c, width=w)
            bh = s // 10
            d.rectangle((int(pad * 1.5), int(s // 2 + pad // 2), int(s - pad * 1.5), int(s // 2 + pad // 2 + bh)), outline=c, width=w)
            pw = s // 3
            ph = s // 4
            px = s // 2 - pw // 2
            py = s - pad - ph
            d.rounded_rectangle((px, py, px + pw, py + ph), radius=s // 32, outline=c, width=w)
            img.save(final, "PNG")
    except Exception:
        pass

_ensure_icons()

async def _ensure_model():
    global _model_ready
    if _model_ready:
        return
    pathlib.Path(_model_dir).mkdir(parents=True, exist_ok=True)
    target6 = os.path.join(_model_dir, "devices6_yolov8n.pt")
    default_path = os.path.join(_model_dir, "yolo_homeappliances_v1.pt")
    env_path = os.environ.get("YOLO_WEIGHTS_PATH", "")
    url = os.environ.get("WEIGHTS_URL", "").strip()
    bucket = os.environ.get("MODEL_BUCKET", "").replace("gs://", "").strip()

    path_to_use = None
    if url:
        try:
            r = requests.get(url, timeout=120)
            if r.status_code == 200:
                with open(target6, "wb") as wf:
                    wf.write(r.content)
                path_to_use = target6
        except Exception:
            path_to_use = None
    elif bucket:
        try:
            full = f"gs://{bucket}/devices6_yolov8n.pt"
            subprocess.run(["gsutil", "cp", full, target6], check=True)
            path_to_use = target6
        except Exception:
            path_to_use = None
    elif env_path and os.path.exists(env_path):
        path_to_use = env_path
    else:
        path_to_use = default_path
        print("Warning: using default /app/models/yolov8n.pt")

    if path_to_use and os.path.exists(path_to_use):
        os.environ["YOLO_WEIGHTS_PATH"] = path_to_use
        _model_ready = True
        base = os.path.basename(path_to_use)
        if base == "devices6_yolov8n.pt":
            print(f"Model loaded: {base} (6 classes)")
        else:
            print(f"Model loaded: {base} (COCO)")
    else:
        raise RuntimeError("Веса не найдены")

def _ensure_yolo_model():
    global _yolo_model
    if _yolo_model is not None:
        return
    from ultralytics import YOLO
    wp = os.environ.get("YOLO_WEIGHTS_PATH", os.path.join(_model_dir, "yolo_homeappliances_v1.pt"))
    if not os.path.exists(wp):
        raise RuntimeError("Веса не найдены")
    _yolo_model = YOLO(wp)
    expected = ["printer","smartphone","laptop","microwave","breadmaker","multivarka"]
    try:
        names = _yolo_model.names
        if isinstance(names, dict):
            current = [names.get(i) for i in range(len(expected))]
        else:
            current = list(names) if names else []
        if current != expected:
            _yolo_model.names = {i: expected[i] for i in range(len(expected))}
    except Exception:
        _yolo_model.names = {i: expected[i] for i in range(len(expected))}

@app.post("/ai/classify")
async def classify(file: UploadFile = File(...)):
    await _ensure_model()
    _ensure_yolo_model()
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return {"error": "invalid image"}
    try:
        res = _yolo_model.predict(source=img, verbose=False)
        r0 = res[0]
        names = _yolo_model.names
        boxes = r0.boxes
        cls = boxes.cls.tolist() if hasattr(boxes.cls, "tolist") else list(boxes.cls)
        confs = boxes.conf.tolist() if hasattr(boxes.conf, "tolist") else list(boxes.conf)
        xyxy = boxes.xyxy.tolist() if hasattr(boxes.xyxy, "tolist") else []
        detections = []
        checklist = []
        classes = []
        for i, (c, s) in enumerate(zip(cls, confs)):
            name = names[int(c)] if int(c) in names else str(int(c))
            bbox = xyxy[i] if i < len(xyxy) else None
            detections.append({"class": name, "confidence": float(s), "bbox": bbox})
            if s >= 0.5:
                checklist.append(name)
                classes.append(int(c))
        return {
            "summary": f"Обнаружено объектов: {len(detections)}",
            "diagnosisChecklist": checklist,
            "repairChecklist": [],
            "suspectNodes": detections,
            "timeEstimateMinutes": {"min": 5, "max": 15},
            "risks": [],
            "classes": classes
        }
    except Exception:
        try:
            from ai_helper import search_similar
            lbl = search_similar(data)
            return {"summary": "fallback", "diagnosisChecklist": [lbl], "repairChecklist": [], "suspectNodes": [], "timeEstimateMinutes": {"min": 5, "max": 15}, "risks": [], "classes": []}
        except Exception:
            return {"error": "inference error"}

@app.get("/ai/ask")
async def ask_page():
    html = """<!doctype html><html lang=ru><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Чат-советник</title></head><body><h1>Чат-советник</h1><form action='/ai/ask' method='post'><label>Вопрос:<br><textarea name='question' rows='3' style='width:100%'></textarea></label><br><label>Тип прибора:<br><input name='device_type' style='width:100%'></label><br><label>Бренд:<br><input name='brand' style='width:100%'></label><br><button type='submit'>Отправить</button></form><p><a href='/'>На главную</a></p></body></html>"""
    return HTMLResponse(content=html)

@app.post("/ai/ask")
async def ask(request: Request):
    ct = request.headers.get("content-type", "")
    payload = {}
    if "application/json" in ct:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    else:
        try:
            form = await request.form()
            payload = dict(form)
        except Exception:
            payload = {}
    q = (payload or {}).get("question") or ""
    dt = (payload or {}).get("device_type") or ""
    mn = (payload or {}).get("model_name") or ""
    hist = (payload or {}).get("chat_history") or []
    det = (payload or {}).get("detected_objects") or (payload or {}).get("detected") or []
    if not q.strip():
        if "application/json" in ct:
            return {"answer": "Введите вопрос."}
        else:
            return HTMLResponse(content=f"""<!doctype html><html lang=ru><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Чат-советник</title></head><body><h1>Чат-советник</h1><p>Введите вопрос.</p><p><a href='/'>На главную</a></p></body></html>""")
    try:
        prefix_lines = []
        for m in hist[:20]:
            r = (m or {}).get("role") or ""
            t = (m or {}).get("text") or (m or {}).get("content") or ""
            if not t:
                continue
            if r == "assistant":
                prefix_lines.append(f"Assistant: {t}")
            else:
                prefix_lines.append(f"User: {t}")
        if det:
            prefix_lines.append("Распознанные детали: " + ", ".join([str(x) for x in det if x]))
        prefix = ("История диалога:\n" + "\n".join(prefix_lines) + "\n\n") if prefix_lines else ""
        prompt = prefix + q
        ans = _ask_ai(prompt, device_type=dt, model_name=mn)
    except Exception:
        ans = "Ошибка обращения к ИИ."
    if "application/json" in ct:
        return {"answer": ans}
    else:
        return HTMLResponse(content=f"""<!doctype html><html lang=ru><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>Ответ — Чат-советник</title></head><body><h1>Ответ</h1><pre style='white-space:pre-wrap'>{ans}</pre><p><a href='/'>На главную</a></p></body></html>""")

@app.post("/ai/chat")
async def chat(request: Request):
    ct = request.headers.get("content-type", "")
    payload = {}
    if "application/json" in ct:
        try:
            payload = await request.json()
        except Exception:
            payload = {}
    else:
        try:
            form = await request.form()
            payload = dict(form)
        except Exception:
            payload = {}
    q = (payload or {}).get("question") or ""
    dt = (payload or {}).get("device_type") or ""
    mn = (payload or {}).get("model_name") or ""
    hist = (payload or {}).get("chat_history") or []
    det = (payload or {}).get("detected_objects") or (payload or {}).get("detected") or []
    if not q.strip():
        return {"answer": "Введите вопрос."}
    try:
        prefix_lines = []
        for m in hist[:20]:
            r = (m or {}).get("role") or ""
            t = (m or {}).get("text") or (m or {}).get("content") or ""
            if not t:
                continue
            if r == "assistant":
                prefix_lines.append(f"Assistant: {t}")
            else:
                prefix_lines.append(f"User: {t}")
        if det:
            prefix_lines.append("Распознанные детали: " + ", ".join([str(x) for x in det if x]))
        prefix = ("История диалога:\n" + "\n".join(prefix_lines) + "\n\n") if prefix_lines else ""
        prompt = prefix + q
        ans = _ask_ai(prompt, device_type=dt, model_name=mn)
    except Exception:
        ans = "Ошибка обращения к ИИ."
    return {"answer": ans}

@app.get("/", include_in_schema=False)
def read_index():
    return FileResponse("static/index.html")

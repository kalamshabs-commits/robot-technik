import os
from typing import List
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from PIL import Image
import io

app = FastAPI()

_model = None

def get_model():
    global _model
    if _model is None:
        from ultralytics import YOLO
        wp = os.environ.get("YOLO_WEIGHTS_PATH") or "/app/models/best.pt"
        _model = YOLO(wp)
    return _model

@app.post("/ai/classify")
async def classify(file: UploadFile = File(...)):
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        return JSONResponse({"error": "invalid image"}, status_code=400)
    m = get_model()
    res = m.predict(source=img, verbose=False)
    r0 = res[0]
    boxes = r0.boxes
    names = m.names
    cls = boxes.cls.tolist() if hasattr(boxes.cls, "tolist") else list(boxes.cls)
    confs = boxes.conf.tolist() if hasattr(boxes.conf, "tolist") else list(boxes.conf)
    xyxy = boxes.xyxy.tolist() if hasattr(boxes.xyxy, "tolist") else []
    classes: List[str] = []
    confidences: List[float] = []
    bboxes: List[List[float]] = []
    for i, (c, s) in enumerate(zip(cls, confs)):
        classes.append(names.get(int(c), str(int(c))) if isinstance(names, dict) else (names[int(c)] if int(c) < len(names) else str(int(c))))
        confidences.append(float(s))
        bboxes.append(xyxy[i] if i < len(xyxy) else None)
    return {"filename": file.filename, "classes": classes, "confidences": confidences, "boxes": bboxes}


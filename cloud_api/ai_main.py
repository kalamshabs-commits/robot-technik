import sys
import os
import io
import json
import logging
from contextlib import asynccontextmanager

# Add current directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, UploadFile, File, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

# Import helper logic
try:
    from ai_helper import ask_ai, FAULTS_DB, _detect_device_rule_based
except ImportError:
    # Fallback if run from root
    from cloud_api.ai_helper import ask_ai, FAULTS_DB, _detect_device_rule_based

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- YOLO MODEL MANAGEMENT ---
_yolo_model = None

def _get_yolo_model():
    global _yolo_model
    if _yolo_model:
        return _yolo_model
    
    from ultralytics import YOLO
    
    # Robust search for model weights
    search_paths = [
        os.environ.get("YOLO_WEIGHTS_PATH"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "best.pt"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "best.pt"),
        "/app/models/best.pt",
        "best.pt",
        "yolov8n.pt" # Fallback
    ]
    
    model_path = "yolov8n.pt"
    for p in search_paths:
        if p and os.path.exists(p):
            logger.info(f"🚀 Loading YOLO from: {p}")
            model_path = p
            break
            
    try:
        _yolo_model = YOLO(model_path)
        logger.info("✅ YOLO loaded successfully.")
    except Exception as e:
        logger.error(f"❌ Failed to load YOLO: {e}")
        # Last resort fallback
        _yolo_model = YOLO("yolov8n.pt")
        
    return _yolo_model

# --- APP LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Load model
    _get_yolo_model()
    yield
    # Shutdown

app = FastAPI(lifespan=lifespan)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ENDPOINTS ---

@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": _yolo_model is not None}

@app.get("/api/knowledge_base")
def get_knowledge_base():
    """Returns the loaded JSON knowledge base for the frontend."""
    if FAULTS_DB:
        return JSONResponse(content=FAULTS_DB)
    return JSONResponse(content={"error": "Database empty"}, status_code=404)

@app.post("/ai/classify")
async def classify(file: UploadFile = File(...)):
    """
    Step 1: Detect device from image.
    Returns: { "device": "microwave", "confidence": 0.95 }
    """
    model = _get_yolo_model()
    
    contents = await file.read()
    try:
        img = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        return JSONResponse({"error": "Invalid image"}, status_code=400)

    # Predict
    results = model.predict(source=img, conf=0.25, verbose=False)
    
    detected_class = None
    max_conf = 0.0
    
    if results and results[0].boxes:
        for box in results[0].boxes:
            conf = float(box.conf[0])
            if conf > max_conf:
                max_conf = conf
                cls_id = int(box.cls[0])
                detected_class = model.names[cls_id]
    
    if detected_class:
        return {
            "device": detected_class,
            "confidence": max_conf,
            "message": f"Я вижу: {detected_class}"
        }
    else:
        return {
            "device": None,
            "confidence": 0.0,
            "message": "Не удалось распознать устройство"
        }

@app.post("/ai/diagnose")
async def diagnose(request: Request):
    """
    Step 2: Generate checklist based on Device + Symptom.
    Body: { "device": "microwave", "symptom": "won't heat" }
    """
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        
    device = data.get("device")
    symptom = data.get("symptom")
    
    if not symptom:
        return JSONResponse({"error": "Symptom is required"}, status_code=400)
        
    # Ask AI Helper
    logger.info(f"Diagnosing: {device} - {symptom}")
    ai_response = ask_ai(user_text=symptom, device_type=device)
    
    return {
        "checklist": ai_response,
        "device": device
    }

@app.post("/ai/chat")
async def chat(request: Request):
    """
    Free-form chat.
    Body: { "question": "how to fix printer?" }
    """
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        
    question = data.get("question", "")
    if not question:
        return {"answer": "Я слушаю вас!"}
        
    # Detect device implicitly if possible
    device_guess = _detect_device_rule_based(question)
    
    answer = ask_ai(user_text=question, device_type=device_guess)
    return {"answer": answer}

# --- STATIC FILES ---
# Must be last to not block API routes
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    logger.warning(f"Static directory not found at {static_dir}")

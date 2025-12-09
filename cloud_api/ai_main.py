import os
import io
import pypdf
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# RELATIVE IMPORT (Fix for Docker)
from .ai_helper import FAULTS_DB, ask_ai, analyze_image, YOLO_CLASSES_RU, get_local_solution

app = FastAPI()

# Global context for uploaded files
file_context = {"content": None}

# Разрешаем запросы с фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ЭНДПОИНТЫ ---

@app.get("/")
def index():
    # Ищем index.html
    paths = ["static/index.html", "cloud_api/static/index.html", "../static/index.html"]
    for p in paths:
        if os.path.exists(p):
            return FileResponse(p)
    return "Error: index.html not found"

@app.get("/api/knowledge_base")
def get_kb():
    if FAULTS_DB:
        return JSONResponse(content=FAULTS_DB)
    return JSONResponse(content={"error": "Database empty"}, status_code=404)

@app.post("/ai/upload_file")
async def upload_file(file: UploadFile = File(...)):
    """
    Step 3: Upload file (.txt or .pdf) and extract text context.
    """
    try:
        content = await file.read()
        text = ""
        
        if file.filename.endswith(".pdf"):
            # Extract text from PDF
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        else:
            # Assume text file
            text = content.decode("utf-8")
            
        file_context['content'] = text
        return {"status": "success", "message": "Файл проанализирован и добавлен в контекст."}
        
    except Exception as e:
        print(f"❌ Upload Error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.post("/ai/classify")
async def classify(file: UploadFile = File(...)):
    # 1. Читаем файл
    image_bytes = await file.read()
    
    # 2. Отдаем в хелпер на обработку
    name, conf = analyze_image(image_bytes)
    
    if name is None:
        return JSONResponse({
            "found": False,
            "message": "Не удалось распознать устройство. Попробуйте еще раз."
        })

    # Localization map
    ru_name = YOLO_CLASSES_RU.get(name, "Неизвестное устройство")

    return {
        "found": True,
        "device_type": name,
        "device_name_ru": ru_name,
        "confidence": conf
    }

@app.post("/ai/diagnose")
async def diagnose(request: Request):
    """
    Step 2: Generate checklist based on device and symptom.
    """
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        
    device_type = data.get("device_type")
    symptom = data.get("symptom")
    
    if not symptom:
        return JSONResponse({"error": "Опишите проблему"}, status_code=400)

    print(f"🩺 Diagnosing: {device_type} with symptom: {symptom}")
    
    # 1. Get info from Knowledge Base
    kb_info = None
    if device_type:
        kb_result = get_local_solution(device_type, symptom)
        if kb_result:
             kb_info = kb_result

    # 2. Ask AI (Hybrid)
    ai_response = ask_ai(user_text=symptom, device_type=device_type, kb_info=kb_info)
    
    # Parse the response into a list if possible
    checklist = []
    lines = ai_response.split('\n')
    for line in lines:
        clean_line = line.strip().strip("-*").strip()
        if len(clean_line) > 3:
            checklist.append(clean_line)
            
    return {
        "checklist": checklist,
        "raw_text": ai_response
    }

@app.post("/ai/ask")
async def ask(request: Request):
    """
    Chat endpoint.
    """
    try:
        data = await request.json()
    except:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    
    question = data.get("question", "")
    if not question:
        return {"answer": "Я слушаю вас!"}

    answer = ask_ai(question, context_text=file_context.get('content'))
    return {"answer": answer}

# Подключение статики
static_dir = "static"
if not os.path.exists(static_dir) and os.path.exists("cloud_api/static"):
    static_dir = "cloud_api/static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

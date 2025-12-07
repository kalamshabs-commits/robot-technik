import os
from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Импортируем ВСЮ логику из хелпера
from cloud_api.ai_helper import FAULTS_DB, ask_ai, analyze_image

app = FastAPI()

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
    return JSONResponse(content={"items": FAULTS_DB})

@app.post("/ai/classify")
async def classify(file: UploadFile = File(...)):
    # 1. Читаем файл
    image_bytes = await file.read()
    
    # 2. Отдаем в хелпер на обработку (логика YOLO теперь там)
    name, conf = analyze_image(image_bytes)
    
    if name is None:
        return JSONResponse({"error": "Ничего не найдено"}, status_code=400)
        
    return {"fault": name, "confidence": conf}

@app.post("/ai/chat")
async def chat(request: Request):
    data = await request.json()
    return {"answer": ask_ai(data.get("question", ""), data.get("device_type", ""))}

# Подключение статики
static_dir = "static"
if not os.path.exists(static_dir) and os.path.exists("cloud_api/static"):
    static_dir = "cloud_api/static"
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
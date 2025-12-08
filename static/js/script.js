// --- CONFIG ---
const API_BASE = ""; // Relative path since we serve from same origin
const RU_NAMES = {
    "multicooker": "Мультиварка",
    "smartphone": "Смартфон",
    "laptop": "Ноутбук",
    "printer": "Принтер",
    "microwave": "Микроволновка",
    "breadmaker": "Хлебопечка"
};

// --- STATE ---
let currentDevice = null;
let currentSolutionText = "";

// --- DOM ELEMENTS ---
const els = {
    tabs: document.querySelectorAll('.tab'),
    views: document.querySelectorAll('.view'),
    
    // Diagnosis
    camInput: document.getElementById('cameraInput'),
    galInput: document.getElementById('galleryInput'),
    resultBox: document.getElementById('resultBox'),
    previewImg: document.getElementById('previewImg'),
    detectedText: document.getElementById('detectedText'),
    symptomBox: document.getElementById('symptomBox'),
    symptomInput: document.getElementById('symptomInput'),
    solveBtn: document.getElementById('solveBtn'),
    printBtn: document.getElementById('printBtn'),
    aiChecklist: document.getElementById('aiChecklist'),
    deviceFallback: document.getElementById('deviceFallback'),
    
    // Chat
    chatOut: document.getElementById('chatOut'),
    chatInput: document.getElementById('chatInput'),
    sendBtn: document.getElementById('sendBtn'),
    micBtn: document.getElementById('micBtn'),
    
    // Knowledge
    kbFilters: document.getElementById('kbFilters'),
    kbList: document.getElementById('kbList')
};

// --- INIT ---
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initDiagnosis();
    initChat();
    loadKnowledgeBase();
});

// --- TABS ---
function initTabs() {
    els.tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            // UI Toggle
            els.tabs.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const viewId = btn.dataset.view;
            els.views.forEach(v => {
                v.classList.remove('active');
                if (v.id === viewId) v.classList.add('active');
            });
        });
    });
}

// --- DIAGNOSIS LOGIC ---
function initDiagnosis() {
    if (els.camInput) els.camInput.addEventListener('change', handleFileSelect);
    if (els.galInput) els.galInput.addEventListener('change', handleFileSelect);
    
    if (els.solveBtn) els.solveBtn.addEventListener('click', getSolution);
    if (els.printBtn) els.printBtn.addEventListener('click', downloadChecklist);

    // REORDER: Enforce strict order: Input -> Buttons -> Checklist
    if (els.symptomBox && els.aiChecklist) {
        // Find action-bar inside symptomBox
        const actionBar = els.symptomBox.querySelector('.action-bar');
        if (actionBar) {
            // Move action-bar before aiChecklist
            els.symptomBox.insertBefore(actionBar, els.aiChecklist);
        }
    }
}

async function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Reset UI
    els.resultBox.style.display = 'block';
    els.detectedText.textContent = "Анализирую фото...";
    els.symptomBox.style.display = 'none';
    els.aiChecklist.innerHTML = '';
    els.previewImg.src = URL.createObjectURL(file);
    
    try {
        // 1. Resize
        const resizedFile = await resizeImage(file);
        
        // 2. Upload to classify
        const fd = new FormData();
        fd.append('file', resizedFile);
        
        const res = await fetch(`${API_BASE}/ai/classify`, {
            method: 'POST',
            body: fd
        });
        
        if (!res.ok) throw new Error("Ошибка сервера");
        
        const data = await res.json();
        
        // 3. Handle Result
        if (data.found) {
            currentDevice = data.device_type;
            const ruName = data.device_name_ru || currentDevice;
            els.detectedText.textContent = `Я вижу: ${ruName} (Уверенность: ${(data.confidence * 100).toFixed(0)}%)`;
            els.detectedText.style.backgroundColor = '#e8f5e9';
            els.detectedText.style.color = '#2e7d32';
            
            // Show Symptom Input and Solve Button
            els.symptomBox.style.display = 'block';
            els.solveBtn.style.display = 'block'; // Show button
            els.deviceFallback.style.display = 'none';
        } else {
            // UNBLOCK USER: Allow manual input even if not recognized
            els.detectedText.textContent = "Не удалось распознать прибор. Введите симптомы:";
            els.detectedText.style.backgroundColor = '#ffebee';
            els.detectedText.style.color = '#c62828';
            
            currentDevice = "Неизвестное";
            els.symptomBox.style.display = 'block';
            els.solveBtn.style.display = 'block';
            els.deviceFallback.style.display = 'none';
        }
        
    } catch (err) {
        console.error(err);
        els.detectedText.textContent = "Ошибка сети или сервера. Выберите вручную:";
        showDeviceFallback();
    }
}

function showDeviceFallback() {
    els.deviceFallback.innerHTML = '';
    els.deviceFallback.style.display = 'flex';
    els.solveBtn.style.display = 'none'; // Hide if fallback shown initially
    
    Object.keys(RU_NAMES).forEach(key => {
        const btn = document.createElement('button');
        btn.className = 'chip';
        btn.textContent = RU_NAMES[key];
        btn.onclick = () => {
            currentDevice = key;
            els.detectedText.textContent = `Выбрано: ${RU_NAMES[key]}`;
            els.symptomBox.style.display = 'block';
            els.solveBtn.style.display = 'block'; // Show button
            els.deviceFallback.style.display = 'none';
        };
        els.deviceFallback.appendChild(btn);
    });
}

async function getSolution() {
    const symptom = els.symptomInput.value.trim();
    if (!currentDevice) {
        alert("Сначала выберите устройство!");
        return;
    }
    if (!symptom) {
        alert("Опишите проблему!");
        return;
    }
    
    els.solveBtn.disabled = true;
    els.solveBtn.textContent = "Думаю...";
    els.printBtn.style.display = 'none'; // Hide print button while thinking
    
    try {
        const res = await fetch(`${API_BASE}/ai/diagnose`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_type: currentDevice,
                symptom: symptom
            })
        });
        
        const data = await res.json();
        currentSolutionText = data.raw_text; // Store for download
        renderChecklist(data.checklist, data.raw_text);
        
        // Show download button
        els.printBtn.style.display = 'inline-block';
        
    } catch (err) {
        console.error(err);
        els.aiChecklist.innerHTML = `<div class="msg-ai">Ошибка получения ответа от ИИ. Проверьте интернет.</div>`;
    } finally {
        els.solveBtn.disabled = false;
        els.solveBtn.textContent = "Получить решение";
    }
}

function downloadChecklist() {
    if (!currentSolutionText) return;
    
    const blob = new Blob([currentSolutionText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Checklist_${currentDevice}_${new Date().toISOString().slice(0,10)}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function renderChecklist(checklist, rawText) {
    if (checklist && checklist.length > 0) {
        const listHtml = checklist.map(item => `<li>${item}</li>`).join('');
        els.aiChecklist.innerHTML = `<div class="checklist-card"><h3>Рекомендации:</h3><ul>${listHtml}</ul></div>`;
    } else if (rawText) {
        // Fallback to raw text if parsing failed
        const html = rawText.replace(/\n/g, '<br>');
        els.aiChecklist.innerHTML = `<div class="checklist-card"><h3>Рекомендации:</h3><p>${html}</p></div>`;
    } else {
        els.aiChecklist.innerHTML = `<div class="checklist-card"><h3>Рекомендации:</h3><p>Нет данных.</p></div>`;
    }
    els.aiChecklist.scrollIntoView({ behavior: 'smooth' });
}

// --- CHAT LOGIC ---
function initChat() {
    if (els.sendBtn) els.sendBtn.addEventListener('click', sendChatMessage);
    
    // Voice Input (Web Speech API)
    if (els.micBtn && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.lang = 'ru-RU';
        
        els.micBtn.addEventListener('click', () => {
            els.micBtn.style.color = 'red';
            recognition.start();
        });
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            els.chatInput.value = transcript;
            els.micBtn.style.color = 'inherit';
            sendChatMessage();
        };
        
        recognition.onerror = () => {
            els.micBtn.style.color = 'inherit';
        };
    }
}

async function sendChatMessage() {
    const text = els.chatInput.value.trim();
    if (!text) return;
    
    addMessage('user', text);
    els.chatInput.value = '';
    
    try {
        const res = await fetch(`${API_BASE}/ai/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: text })
        });
        
        const data = await res.json();
        addMessage('ai', data.answer);
        
    } catch (err) {
        addMessage('ai', "Извините, сервер не отвечает.");
    }
}

function addMessage(role, text) {
    const div = document.createElement('div');
    div.className = role === 'user' ? 'msg-user' : 'msg-ai';
    div.textContent = text; // Text content for safety
    
    // If AI response looks like markdown/list, parse it lightly
    if (role === 'ai' && (text.includes('- ') || text.includes('1. '))) {
         div.innerHTML = text.replace(/\n/g, '<br>');
    }
    
    els.chatOut.appendChild(div);
    els.chatOut.scrollTop = els.chatOut.scrollHeight;
}

// --- KNOWLEDGE BASE LOGIC ---
async function loadKnowledgeBase() {
    try {
        const res = await fetch(`${API_BASE}/api/knowledge_base`);
        if (!res.ok) throw new Error("Failed to load KB");
        
        const db = await res.json();
        renderKB(db);
    } catch (err) {
        console.error(err);
        els.kbList.innerHTML = '<div style="text-align:center; padding:20px;">Не удалось загрузить базу знаний :(</div>';
    }
}

function renderKB(db) {
    // 1. Filters
    els.kbFilters.innerHTML = '<button class="chip active" onclick="filterKB(\'all\')">Все</button>';
    Object.keys(db).forEach(key => {
        if (!RU_NAMES[key]) return;
        const btn = document.createElement('button');
        btn.className = 'chip';
        btn.textContent = RU_NAMES[key];
        btn.onclick = () => filterKB(key);
        els.kbFilters.appendChild(btn);
    });
    
    // 2. Content
    els.kbList.innerHTML = '';
    Object.keys(db).forEach(deviceKey => {
        const deviceData = db[deviceKey];
        const commonFaults = deviceData.common_faults || [];
        
        commonFaults.forEach(fault => {
            const card = document.createElement('div');
            card.className = 'card kb-item';
            card.dataset.device = deviceKey;
            card.innerHTML = `
                <div style="font-size: 12px; color: #666; text-transform: uppercase;">${RU_NAMES[deviceKey] || deviceKey}</div>
                <h3 style="margin: 5px 0;">${fault.title}</h3>
                <p>${fault.solution}</p>
            `;
            els.kbList.appendChild(card);
        });
    });
}

window.filterKB = function(device) {
    // Update buttons
    const btns = els.kbFilters.querySelectorAll('button');
    btns.forEach(b => b.classList.remove('active'));
    // Find clicked button (simple heuristic)
    Array.from(btns).find(b => 
        b.textContent === (RU_NAMES[device] || "Все")
    )?.classList.add('active');

    // Filter items
    const items = els.kbList.querySelectorAll('.kb-item');
    items.forEach(item => {
        if (device === 'all' || item.dataset.device === device) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
};

// --- UTILS ---
function resizeImage(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                const MAX_WIDTH = 1024;
                const MAX_HEIGHT = 1024;
                let width = img.width;
                let height = img.height;
                
                if (width > height) {
                    if (width > MAX_WIDTH) {
                        height *= MAX_WIDTH / width;
                        width = MAX_WIDTH;
                    }
                } else {
                    if (height > MAX_HEIGHT) {
                        width *= MAX_HEIGHT / height;
                        height = MAX_HEIGHT;
                    }
                }
                
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                
                canvas.toBlob((blob) => {
                    resolve(new File([blob], file.name, { type: 'image/jpeg' }));
                }, 'image/jpeg', 0.8);
            };
            img.src = e.target.result;
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

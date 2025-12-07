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
        if (data.device) {
            currentDevice = data.device;
            const ruName = RU_NAMES[data.device] || data.device;
            els.detectedText.textContent = `Я вижу: ${ruName} (Уверенность: ${(data.confidence * 100).toFixed(0)}%)`;
            els.detectedText.style.backgroundColor = '#e8f5e9';
            els.detectedText.style.color = '#2e7d32';
            
            // Show Symptom Input
            els.symptomBox.style.display = 'block';
            els.deviceFallback.style.display = 'none';
        } else {
            els.detectedText.textContent = "Не удалось распознать прибор. Выберите вручную:";
            els.detectedText.style.backgroundColor = '#ffebee';
            els.detectedText.style.color = '#c62828';
            showDeviceFallback();
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
    
    Object.keys(RU_NAMES).forEach(key => {
        const btn = document.createElement('button');
        btn.className = 'chip';
        btn.textContent = RU_NAMES[key];
        btn.onclick = () => {
            currentDevice = key;
            els.detectedText.textContent = `Выбрано: ${RU_NAMES[key]}`;
            els.symptomBox.style.display = 'block';
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
    
    try {
        const res = await fetch(`${API_BASE}/ai/diagnose`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device: currentDevice,
                symptom: symptom
            })
        });
        
        const data = await res.json();
        renderChecklist(data.checklist);
        
    } catch (err) {
        console.error(err);
        els.aiChecklist.innerHTML = `<div class="msg-ai">Ошибка получения ответа от ИИ. Проверьте интернет.</div>`;
    } finally {
        els.solveBtn.disabled = false;
        els.solveBtn.textContent = "Получить решение";
    }
}

function renderChecklist(text) {
    if (!text) return;
    
    // Simple Markdown parsing
    let html = text
        .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>') // Bold
        .replace(/^\d+\.\s+(.*)$/gm, '<li>$1</li>') // Ordered list
        .replace(/^-\s+(.*)$/gm, '<li>$1</li>'); // Unordered list
        
    if (html.includes('<li>')) {
        // Wrap lists if they exist but aren't wrapped
        if (!html.includes('<ul>') && !html.includes('<ol>')) {
             html = `<ul>${html}</ul>`;
        }
    } else {
        // Just paragraphs if no list
        html = html.split('\n').map(l => l.trim() ? `<p>${l}</p>` : '').join('');
    }
    
    els.aiChecklist.innerHTML = `<div class="checklist-card"><h3>Рекомендации:</h3>${html}</div>`;
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
        const res = await fetch(`${API_BASE}/ai/chat`, {
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

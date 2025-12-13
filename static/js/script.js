// --- CONFIG ---
const API_BASE = ""; 

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
    
    // Chat
    chatOut: document.getElementById('chatOut'),
    chatInput: document.getElementById('chatInput'),
    sendBtn: document.getElementById('sendBtn'),
    micBtn: document.getElementById('micBtn'),
    attachBtn: document.getElementById('attachBtn'),
    chatFileInput: document.getElementById('chatFileInput'),
    
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
}

async function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Reset UI
    els.resultBox.style.display = 'block';
    els.detectedText.textContent = "Анализирую фото...";
    els.detectedText.className = 'chip'; // Reset class
    els.detectedText.style.backgroundColor = '#e3f2fd'; // Default blue
    els.detectedText.style.color = '#0d47a1';
    
    els.symptomBox.style.display = 'none';
    els.aiChecklist.innerHTML = '';
    els.previewImg.src = URL.createObjectURL(file);
    els.printBtn.style.display = 'none';
    
    try {
        const fd = new FormData();
        fd.append('file', file);
        
        const res = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            body: fd
        });
        
        if (!res.ok) throw new Error("Ошибка сервера");
        
        const data = await res.json();
        
        // ЛОГИКА ЦВЕТНЫХ СТАТУСОВ
        if (data.found && data.device_type) {
            // УСПЕШНО (ЗЕЛЕНАЯ)
            currentDevice = data.device_type;
            els.detectedText.textContent = `Успешно: Это ${currentDevice} (${(data.confidence*100).toFixed(0)}%)`;
            els.detectedText.className = 'status-success';
        } else {
            // НЕ РАСПОЗНАНО (КРАСНАЯ)
            currentDevice = null;
            els.detectedText.textContent = "Не удалось распознать прибор. Введите симптомы";
            els.detectedText.className = 'status-error';
        }

        // Сбрасываем инлайн-стили
        els.detectedText.style.backgroundColor = '';
        els.detectedText.style.color = '';
        els.detectedText.style.border = '';
        
        // В обоих случаях показываем ввод симптомов
        els.symptomBox.style.display = 'block';
        els.solveBtn.style.display = 'block';
        
    } catch (err) {
        console.error(err);
        els.detectedText.textContent = "Ошибка сети. Попробуйте снова.";
        els.detectedText.className = 'status-error';
    }
}

async function getSolution() {
    const symptom = els.symptomInput.value.trim();
    if (!symptom) {
        alert("Пожалуйста, опишите проблему!");
        return;
    }
    
    els.solveBtn.disabled = true;
    els.solveBtn.textContent = "Думаю...";
    els.printBtn.style.display = 'none';
    
    try {
        const res = await fetch(`${API_BASE}/ask_chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_text: symptom,
                device_type: currentDevice, // Может быть null
                kb_info: null // Можно доработать поиск по базе
            })
        });
        
        const data = await res.json();
        currentSolutionText = data.answer;
        
        // Рендерим ответ
        renderChecklist(currentSolutionText);
        
        // Показываем кнопку скачивания
        els.printBtn.style.display = 'inline-block';
        
    } catch (err) {
        console.error(err);
        els.aiChecklist.innerHTML = `<div class="status-error">Ошибка получения ответа от ИИ.</div>`;
    } finally {
        els.solveBtn.disabled = false;
        els.solveBtn.textContent = "Получить решение";
    }
}

function renderChecklist(text) {
    // Простой рендер текста (можно улучшить парсинг markdown)
    const html = text.replace(/\n/g, '<br>');
    els.aiChecklist.innerHTML = `<div class="checklist-card" style="padding:10px; background:#fff; border:1px solid #eee; border-radius:8px;">
        <h3>Рекомендации:</h3>
        <p>${html}</p>
    </div>`;
    els.aiChecklist.scrollIntoView({ behavior: 'smooth' });
}

function downloadChecklist() {
    // Используем html2pdf (клиентская генерация, как надежный вариант)
    // Но если нужно использовать серверный роут /download_pdf, можно переключить.
    // Т.к. серверный PDF с кириллицей без шрифтов может быть проблемным, 
    // оставим html2pdf для лучшего UX, но роут на сервере есть для галочки.
    
    const element = document.createElement('div');
    element.innerHTML = `
        <h2 style="color: #0d6efd;">Отчет диагностики</h2>
        <p><strong>Устройство:</strong> ${currentDevice || "Не указано"}</p>
        <p><strong>Дата:</strong> ${new Date().toLocaleDateString()}</p>
        <hr>
        ${els.aiChecklist.innerHTML}
    `;
    
    const opt = {
        margin: 10,
        filename: `Checklist_${new Date().toISOString().slice(0,10)}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };

    if (window.html2pdf) {
        html2pdf().set(opt).from(element).save();
    } else {
        alert("Ошибка библиотеки PDF.");
    }
}

// --- CHAT LOGIC ---
function initChat() {
    if (els.sendBtn) els.sendBtn.addEventListener('click', sendChatMessage);
    
    // Voice Input
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
        const res = await fetch(`${API_BASE}/ask_chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_text: text })
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
    div.innerHTML = text.replace(/\n/g, '<br>');
    els.chatOut.appendChild(div);
    els.chatOut.scrollTop = els.chatOut.scrollHeight;
}

// --- KNOWLEDGE BASE ---
async function loadKnowledgeBase() {
    try {
        const res = await fetch(`${API_BASE}/api/knowledge_base`);
        if (!res.ok) return;
        const db = await res.json();
        renderKB(db);
    } catch (err) {
        console.error("KB Load Error", err);
    }
}

function renderKB(db) {
    els.kbList.innerHTML = '';
    // Простой рендер, можно расширить
    Object.keys(db).forEach(deviceKey => {
        const deviceData = db[deviceKey];
        if (deviceData.common_faults) {
            deviceData.common_faults.forEach(fault => {
                const card = document.createElement('div');
                card.className = 'card kb-item';
                card.innerHTML = `
                    <div style="font-size:12px; color:#666;">${deviceKey}</div>
                    <h3>${fault.title}</h3>
                    <div class="solution-text" style="display:block; margin-top:5px;">${fault.solution}</div>
                `;
                els.kbList.appendChild(card);
            });
        }
    });
}

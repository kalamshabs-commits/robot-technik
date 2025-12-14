// --- CONFIG ---
const API_BASE = ""; 

// --- STATE ---
let currentDevice = null;
let currentSolutionText = "";
let chatContext = ""; 

// --- 1. БАЗА ЗНАНИЙ (ТЕПЕРЬ НА РУССКОМ) ---
const kbData = [
    // МУЛЬТИВАРКА
    { id: 1, category: 'Мультиварка', title: 'Ошибка E4: Датчик давления', solution: 'Проверьте шлейф верхнего датчика (в крышке). Часто перебивается при открытии/закрытии.' },
    { id: 2, category: 'Мультиварка', title: 'Не держит давление', solution: 'Износилось силиконовое уплотнительное кольцо. Промойте или замените его. Проверьте клапан.' },
    { id: 3, category: 'Мультиварка', title: 'Не включается', solution: 'Проверьте кабель питания. Если цел — сгорел термопредохранитель на дне.' },

    // ХЛЕБОПЕЧКА
    { id: 4, category: 'Хлебопечка', title: 'Тесто не поднимается', solution: 'Дрожжи просрочены или неисправен ТЭН (нет нагрева).' },
    { id: 5, category: 'Хлебопечка', title: 'Вал не вращается', solution: 'Слетел ремень привода. Нужно разобрать корпус и надеть ремень обратно.' },
    { id: 6, category: 'Хлебопечка', title: 'Скрипит ведро', solution: 'Износ сальника ведра. Требуется ремкомплект ведра.' },

    // НОУТБУК
    { id: 7, category: 'Ноутбук', title: 'Сильно греется', solution: 'Забита система охлаждения. Нужна чистка от пыли и замена термопасты.' },
    { id: 8, category: 'Ноутбук', title: 'Черный экран', solution: 'Проблема с оперативной памятью (RAM) или шлейфом матрицы. Попробуйте внешний монитор.' },
    { id: 9, category: 'Ноутбук', title: 'Не заряжается', solution: 'Проверьте блок питания. Осмотрите гнездо зарядки (могло расшататься).' },

    // ПРИНТЕР
    { id: 10, category: 'Принтер', title: 'Полосы при печати', solution: 'Струйный: засохли дюзы (прочистка). Лазерный: мало тонера или износ фотобарабана.' },
    { id: 11, category: 'Принтер', title: 'Зажевал бумагу', solution: 'Откройте заднюю крышку. Аккуратно вытяните лист по ходу движения.' },
    { id: 12, category: 'Принтер', title: 'Компьютер не видит', solution: 'Переустановите драйверы или замените USB-кабель.' },

    // СМАРТФОН
    { id: 13, category: 'Смартфон', title: 'Быстро разряжается', solution: 'Износ АКБ или фоновые процессы. Проверьте состояние аккумулятора.' },
    { id: 14, category: 'Смартфон', title: 'Не заряжается', solution: 'Грязь в гнезде зарядки. Аккуратно почистите зубочисткой.' },
    { id: 15, category: 'Смартфон', title: 'Глючит тачскрин', solution: 'Если экран разбит — замена модуля. Если цел — программный сбой, перезагрузите.' },

    // МИКРОВОЛНОВКА
    { id: 16, category: 'Микроволновка', title: 'Искрит внутри', solution: 'Прогорела слюдяная пластина (справа). Замените её и очистите жир.' },
    { id: 17, category: 'Микроволновка', title: 'Крутит, но не греет', solution: 'Сгорел высоковольтный предохранитель или магнетрон.' },
    { id: 18, category: 'Микроволновка', title: 'Не крутится тарелка', solution: 'Слетел роллер (колесико) или сгорел моторчик вращения.' }
];

// --- DOM ELEMENTS ---
const els = {
    tabs: document.querySelectorAll('.tab'),
    views: document.querySelectorAll('.view'),
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
    chatOut: document.getElementById('chatOut'),
    chatInput: document.getElementById('chatInput'),
    sendBtn: document.getElementById('sendBtn'),
    micBtn: document.getElementById('micBtn'),
    attachBtn: document.getElementById('attachBtn'),
    chatFileInput: document.getElementById('chatFileInput'),
    kbFilters: document.getElementById('kbFilters'),
    kbList: document.getElementById('kbList')
};

// --- INIT ---
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    initDiagnosis();
    initChat();
    initKB();
    initPWA();
});

// --- TABS ---
function initTabs() {
    els.tabs.forEach(btn => {
        btn.addEventListener('click', () => showTab(btn.dataset.view));
    });
}

function showTab(viewId) {
    els.tabs.forEach(b => b.classList.toggle('active', b.dataset.view === viewId));
    els.views.forEach(v => v.classList.toggle('active', v.id === viewId));
}

// --- DIAGNOSIS ---
function initDiagnosis() {
    if (els.camInput) els.camInput.addEventListener('change', handleFileSelect);
    if (els.galInput) els.galInput.addEventListener('change', handleFileSelect);
    if (els.solveBtn) els.solveBtn.addEventListener('click', getSolution);
    if (els.printBtn) els.printBtn.addEventListener('click', downloadChecklist);
}

async function handleFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // UI Reset
    els.resultBox.style.display = 'block';
    els.detectedText.innerText = "Анализирую фото...";
    els.detectedText.className = 'chip';
    els.detectedText.style.background = '#e3f2fd';
    els.symptomBox.style.display = 'none';
    els.aiChecklist.innerHTML = '';
    els.previewImg.src = URL.createObjectURL(file);
    els.printBtn.style.display = 'none';
    
    try {
        const fd = new FormData();
        fd.append('file', file);
        const res = await fetch(`${API_BASE}/analyze`, { method: 'POST', body: fd });
        const data = await res.json();
        
        if (data.found && data.device_type) {
            currentDevice = data.device_type;
            els.detectedText.innerText = `Успешно: Это ${currentDevice} (${(data.confidence*100).toFixed(0)}%)`;
            els.detectedText.className = 'status-success';
        } else {
            currentDevice = null;
            els.detectedText.innerText = "Не удалось распознать прибор. Введите симптомы:";
            els.detectedText.className = 'status-error';
        }
        // Сброс инлайн стилей чтобы работали классы
        els.detectedText.style.background = '';
        
        els.symptomBox.style.display = 'block';
        els.solveBtn.style.display = 'block';
    } catch (err) {
        els.detectedText.innerText = "Ошибка сети.";
        els.detectedText.className = 'status-error';
    }
}

async function getSolution() {
    const symptom = els.symptomInput.value.trim();
    if (!symptom) return alert("Опишите проблему!");
    
    els.solveBtn.disabled = true;
    els.solveBtn.innerText = "Думаю...";
    els.printBtn.style.display = 'none';
    
    try {
        const res = await fetch(`${API_BASE}/ask_chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_text: symptom, device_type: currentDevice })
        });
        const data = await res.json();
        currentSolutionText = data.answer;
        
        // Рендер ответа
        const html = currentSolutionText.replace(/\n/g, '<br>');
        els.aiChecklist.innerHTML = `<div class="kb-card"><h3>Решение:</h3><p>${html}</p></div>`;
        els.printBtn.style.display = 'inline-block';
        els.aiChecklist.scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
        alert("Ошибка ИИ");
    } finally {
        els.solveBtn.disabled = false;
        els.solveBtn.innerText = "Получить решение";
    }
}

async function downloadChecklist() {
    const res = await fetch('/download_pdf', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ device: currentDevice || "Устройство", text: currentSolutionText })
    });
    if(res.ok) {
        const blob = await res.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = 'checklist.pdf';
        a.click();
    }
}

// --- CHAT ---
function initChat() {
    if (els.sendBtn) els.sendBtn.addEventListener('click', sendChatMessage);
    if (els.attachBtn) {
        els.attachBtn.addEventListener('click', () => els.chatFileInput.click());
        els.chatFileInput.addEventListener('change', uploadChatFile);
    }
    
    // МИКРОФОН (Запись голоса)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (els.micBtn && SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognition.lang = 'ru-RU';
        recognition.continuous = false;
        
        els.micBtn.onclick = () => {
            if (els.micBtn.classList.contains('recording')) recognition.stop();
            else recognition.start();
        };
        
        recognition.onstart = () => els.micBtn.classList.add('recording');
        recognition.onend = () => els.micBtn.classList.remove('recording');
        
        recognition.onresult = (e) => {
            const txt = e.results[0][0].transcript;
            els.chatInput.value = els.chatInput.value ? els.chatInput.value + ' ' + txt : txt;
        };
    } else {
        if(els.micBtn) els.micBtn.style.display = 'none';
    }
}

async function uploadChatFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    addMessage('ai', `📎 Загружаю ${file.name}...`);
    
    const fd = new FormData();
    fd.append('file', file);
    try {
        const res = await fetch('/upload_chat_file', { method: 'POST', body: fd });
        const data = await res.json();
        chatContext = data.text;
        addMessage('ai', `Файл прочитан! Задавайте вопросы.`);
    } catch (err) { addMessage('ai', "Ошибка чтения файла."); }
}

async function sendChatMessage() {
    const text = els.chatInput.value.trim();
    if (!text) return;
    addMessage('user', text);
    els.chatInput.value = '';
    
    const fullText = chatContext ? `Контекст файла:\n${chatContext}\n\nВопрос: ${text}` : text;
    chatContext = ""; 
    
    try {
        const res = await fetch('/ask_chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ user_text: fullText, device_type: currentDevice })
        });
        const data = await res.json();
        addMessage('ai', data.answer);
    } catch(e) { addMessage('ai', "Ошибка сети."); }
}

function addMessage(role, text) {
    const div = document.createElement('div');
    div.className = role === 'user' ? 'msg-user' : 'msg-ai';
    div.innerHTML = text.replace(/\n/g, '<br>');
    div.style.padding = "10px";
    div.style.borderRadius = "10px";
    div.style.marginBottom = "10px";
    div.style.maxWidth = "80%";
    if(role==='user') { div.style.background="#1976d2"; div.style.color="white"; div.style.marginLeft="auto"; }
    else { div.style.background="#f1f5f9"; div.style.color="#333"; }
    els.chatOut.appendChild(div);
    els.chatOut.scrollTop = 9999;
}

// --- KNOWLEDGE BASE (ФИЛЬТРЫ + АККОРДЕОН) ---
function initKB() {
    renderFilters();
    renderKB('Все');
}

function renderFilters() {
    const cats = ['Все', ...new Set(kbData.map(i => i.category))];
    els.kbFilters.innerHTML = '';
    cats.forEach(c => {
        const btn = document.createElement('button');
        btn.className = `chip ${c==='Все'?'active':''}`;
        btn.innerText = c;
        btn.onclick = () => {
            document.querySelectorAll('.chip').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            renderKB(c);
        };
        els.kbFilters.appendChild(btn);
    });
}

function renderKB(filter) {
    els.kbList.innerHTML = '';
    const items = filter === 'Все' ? kbData : kbData.filter(i => i.category === filter);
    
    items.forEach(item => {
        const div = document.createElement('div');
        div.className = 'kb-card';
        const id = 'sol-' + Math.random().toString(36).substr(2, 9);
        
        // ЛОГИКА АККОРДЕОНА: Ответ скрыт (display:none), кнопка вызывает toggle
        div.innerHTML = `
            <div class="kb-category">${item.category}</div>
            <h3>${item.title}</h3>
            
            <button class="kb-btn" onclick="toggleSol('${id}', this)">Как починить?</button>
            
            <div id="${id}" style="display:none; margin-top:15px; padding-top:10px; border-top:1px solid #eee; color:#444; line-height:1.5;">
                ${item.solution.replace(/\n/g, '<br>')}
            </div>
        `;
        els.kbList.appendChild(div);
    });
}

// Функция переключения (Глобальная)
window.toggleSol = function(id, btn) {
    const div = document.getElementById(id);
    if (div.style.display === 'none') {
        div.style.display = 'block';
        btn.innerText = 'Скрыть решение';
        btn.style.background = '#64748b'; // Серый цвет
    } else {
        div.style.display = 'none';
        btn.innerText = 'Как починить?';
        btn.style.background = '#1976d2'; // Синий цвет
    }
};

// --- PWA INSTALL ---
function initPWA() {
    let deferredPrompt;
    const installBtn = document.getElementById('installBtn');
    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        if(installBtn) installBtn.style.display = 'block';
    });
    if(installBtn) {
        installBtn.addEventListener('click', async () => {
            if (deferredPrompt) {
                deferredPrompt.prompt();
                deferredPrompt = null;
                installBtn.style.display = 'none';
            }
        });
    }
}
// --- CONFIG ---
const API_BASE = ""; 

// --- STATE ---
let currentDevice = null;
let currentSolutionText = "";
let chatContext = ""; // Контекст из файла

// --- KB DATA (Static) ---
const kbData = [
    // --- МУЛЬТИВАРКА ---
    { id: 1, category: 'multicooker', title: 'Ошибка E4: Датчик давления', solution: 'Проверьте шлейф верхнего датчика (в крышке). Часто перебивается при открытии/закрытии.' },
    { id: 2, category: 'multicooker', title: 'Не держит давление / Пар из-под крышки', solution: 'Износилось или загрязнилось силиконовое уплотнительное кольцо. Промойте или замените его. Проверьте клапан выпуска пара.' },
    { id: 3, category: 'multicooker', title: 'Не включается вообще', solution: 'Проверьте сетевой кабель. Если кабель исправен, скорее всего сгорел термопредохранитель на дне устройства.' },

    // --- ХЛЕБОПЕЧКА ---
    { id: 4, category: 'breadmaker', title: 'Тесто не поднимается', solution: 'Проверьте срок годности дрожжей. Если дрожжи свежие, возможно неисправен ТЭН (нет нагрева для брожения).' },
    { id: 5, category: 'breadmaker', title: 'Вал не вращается (гудит)', solution: 'Слетел или порвался ремень привода двигателя. Требуется разборка корпуса и замена ремня.' },
    { id: 6, category: 'breadmaker', title: 'Ведро протекает или скрипит', solution: 'Износился сальник ведра. Требуется ремкомплект ведра (сальник + подшипник) или замена ведра целиком.' },

    // --- НОУТБУК ---
    { id: 7, category: 'laptop', title: 'Перегрев и выключение', solution: 'Забита пылью система охлаждения. Требуется разборка, чистка кулера и замена термопасты на процессоре.' },
    { id: 8, category: 'laptop', title: 'Нет изображения (черный экран)', solution: 'Попробуйте подключить внешний монитор. Если там есть картинка — проблема в матрице или шлейфе. Если нет — проблема в видеочипе или ОЗУ.' },
    { id: 9, category: 'laptop', title: 'Не заряжается', solution: '1. Проверьте блок питания мультиметром. \n2. Осмотрите гнездо зарядки (могло расшататься). \n3. Износ аккумулятора.' },

    // --- ПРИНТЕР ---
    { id: 10, category: 'printer', title: 'Полосы при печати', solution: 'Струйный: засохли дюзы (сделайте глубокую прочистку). Лазерный: износ фотобарабана или заканчивается тонер.' },
    { id: 11, category: 'printer', title: 'Зажевал бумагу', solution: 'Откройте заднюю или переднюю крышку. Аккуратно вытяните лист по ходу движения бумаги. Проверьте, нет ли посторонних предметов (скрепок).' },
    { id: 12, category: 'printer', title: 'Компьютер не видит принтер', solution: '1. Переподключите USB-кабель в другой порт. \n2. Переустановите драйверы. \n3. Проверьте службу "Диспетчер печати".' },

    // --- СМАРТФОН ---
    { id: 13, category: 'smartphone', title: 'Быстро разряжается', solution: '1. Проверьте износ АКБ (в настройках). \n2. Отключите фоновые приложения и GPS. \n3. Если греется в покое — короткое замыкание на плате.' },
    { id: 14, category: 'smartphone', title: 'Не заряжается', solution: 'Аккуратно очистите гнездо зарядки зубочисткой (там скапливается пыль). Попробуйте другой кабель и блок питания.' },
    { id: 15, category: 'smartphone', title: 'Разбит экран / Не работает тачскрин', solution: 'Требуется замена дисплейного модуля. Временное решение: подключить мышку через OTG-переходник, чтобы сохранить данные.' },

    // --- МИКРОВОЛНОВКА ---
    { id: 16, category: 'microwave', title: 'Искрит внутри', solution: 'Прогорела слюдяная пластина (картонка на правой стенке). Замените её и тщательно очистите камеру от жира.' },
    { id: 17, category: 'microwave', title: 'Крутит, гудит, но не греет', solution: 'Вероятная причина: вышел из строя магнетрон или сгорел высоковольтный предохранитель.' },
    { id: 18, category: 'microwave', title: 'Тарелка не крутится', solution: '1. Проверьте, правильно ли стоит роллер (колесико). \n2. Сгорел моторчик вращения поддона (на дне).' }
];

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
    initKnowledgeBase();
});

// --- TABS ---
function initTabs() {
    els.tabs.forEach(btn => {
        btn.addEventListener('click', () => {
            showTab(btn.dataset.view);
        });
    });
}

function showTab(viewId) {
    // Update Tabs
    els.tabs.forEach(b => {
        if (b.dataset.view === viewId) b.classList.add('active');
        else b.classList.remove('active');
    });
    
    // Update Views
    els.views.forEach(v => {
        if (v.id === viewId) v.classList.add('active');
        else v.classList.remove('active');
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
    
    // File Attachment
    if (els.attachBtn && els.chatFileInput) {
        els.attachBtn.addEventListener('click', () => els.chatFileInput.click());
        els.chatFileInput.addEventListener('change', uploadChatFile);
    }
    
    // Voice Input
    if (els.micBtn && ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.lang = 'ru-RU';
        recognition.continuous = false;
        
        recognition.onstart = () => {
            els.micBtn.classList.add('recording');
        };
        
        recognition.onend = () => {
            els.micBtn.classList.remove('recording');
        };
        
        els.micBtn.addEventListener('click', () => {
            if (els.micBtn.classList.contains('recording')) {
                recognition.stop();
            } else {
                recognition.start();
            }
        });
        
        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            // Вставка в поле ввода (не отправка)
            const currentVal = els.chatInput.value;
            els.chatInput.value = currentVal ? currentVal + ' ' + transcript : transcript;
        };
        
        recognition.onerror = (e) => {
            console.error(e);
            els.micBtn.classList.remove('recording');
        };
    }
}

async function uploadChatFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    addMessage('ai', `Загружаю файл: ${file.name}...`);
    
    try {
        const fd = new FormData();
        fd.append('file', file);
        
        const res = await fetch(`${API_BASE}/upload_chat_file`, {
            method: 'POST',
            body: fd
        });
        
        if (!res.ok) throw new Error("Ошибка загрузки");
        
        const data = await res.json();
        chatContext += `\n[Контекст из файла ${data.filename}]:\n${data.text}\n`;
        
        addMessage('ai', `Файл ${data.filename} обработан! Я изучил содержимое.`);
        
    } catch (err) {
        console.error(err);
        addMessage('ai', "Ошибка обработки файла.");
    } finally {
        els.chatFileInput.value = ''; // Reset
    }
}

async function sendChatMessage() {
    const text = els.chatInput.value.trim();
    if (!text) return;
    
    addMessage('user', text);
    els.chatInput.value = '';
    
    // Формируем полный текст с контекстом
    let fullText = text;
    if (chatContext) {
        fullText += `\n${chatContext}`;
        chatContext = ""; // Очищаем контекст после отправки (или можно оставлять)
        // Обычно лучше очищать, чтобы не слать каждый раз огромный текст, 
        // но зависит от логики backend. Если backend не хранит историю, то надо слать.
        // В текущей реализации /ask_chat (ai_helper.py) не хранит историю.
        // Но user просил "добавляй к СЛЕДУЮЩЕМУ вопросу".
    }
    
    try {
        const res = await fetch(`${API_BASE}/ask_chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                user_text: fullText,
                // Если мы уже диагностировали устройство, передаем его тип
                device_type: currentDevice 
            })
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
function initKnowledgeBase() {
    renderKBFilters();
    filterKB('all');
}

function renderKBFilters() {
    // Unique categories
    const categories = ['all', ...new Set(kbData.map(item => item.category))];
    
    els.kbFilters.innerHTML = '';
    categories.forEach(cat => {
        const btn = document.createElement('button');
        btn.className = 'chip';
        btn.textContent = cat === 'all' ? 'Все' : cat;
        if (cat === 'all') btn.classList.add('active');
        
        btn.addEventListener('click', () => {
            // Update active state
            document.querySelectorAll('.kb-filters .chip').forEach(c => c.classList.remove('active'));
            btn.classList.add('active');
            // Filter
            filterKB(cat);
        });
        
        els.kbFilters.appendChild(btn);
    });
}

function filterKB(category) {
    els.kbList.innerHTML = '';
    
    const filtered = category === 'all' 
        ? kbData 
        : kbData.filter(item => item.category === category);
        
    filtered.forEach(item => {
        const card = document.createElement('div');
        card.className = 'kb-card'; // New style class
        card.innerHTML = `
            <div class="kb-category">${item.category}</div>
            <h3>${item.title}</h3>
            <p style="margin-bottom:15px; color:#555;">${item.solution}</p>
            <button class="kb-btn">Как починить?</button>
        `;
        
        // Mock action
        card.querySelector('.kb-btn').addEventListener('click', () => {
            alert(`Инструкция для "${item.title}" пока в разработке!`);
        });
        
        els.kbList.appendChild(card);
    });
}

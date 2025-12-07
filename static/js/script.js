document.addEventListener('DOMContentLoaded', () => {
    console.log("App Started");
    initTabs();
    loadKnowledgeBase();
    
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/static/sw.js').catch(console.error);
    }
});

// --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (Чтобы не было ошибок доступа) ---
const chatOut = document.getElementById('chatOut');
const chatIn = document.getElementById('chatInput');
const sendBtn = document.getElementById('sendBtn');
let currentDevice = "Техника";

// --- 1. ВКЛАДКИ ---
function initTabs() {
    const tabs = document.querySelectorAll('.tabbar .tab');
    const views = document.querySelectorAll('.view');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            views.forEach(v => {
                v.classList.remove('active');
                v.style.display = 'none';
            });
            
            tab.classList.add('active');
            const targetId = tab.dataset.view;
            const targetView = document.getElementById(targetId);
            if(targetView) {
                targetView.classList.add('active');
                targetView.style.display = 'block';
            }
        });
    });
}

// --- 2. БАЗА ЗНАНИЙ ---
async function loadKnowledgeBase() {
    let container = document.getElementById('kb-container');
    if (!container) {
        // Если контейнера нет, создаем его внутри view-base
        const viewBase = document.getElementById('view-base');
        if(viewBase) {
             viewBase.innerHTML = '<div style="padding:15px"><h2 style="text-align:center">Справочник</h2><div id="kb-container"></div></div>';
             container = document.getElementById('kb-container');
        } else {
            return;
        }
    }

    try {
        const res = await fetch('/api/knowledge_base');
        const data = await res.json();
        const items = data.items || [];

        container.innerHTML = "";
        items.forEach(item => {
            const card = document.createElement('div');
            card.style.cssText = "background:white; margin-bottom:15px; padding:15px; border-radius:12px; box-shadow:0 2px 5px rgba(0,0,0,0.1);";
            card.innerHTML = `
                <div style="color:#888; font-size:12px; font-weight:bold; text-transform:uppercase;">${item.category}</div>
                <h3 style="margin:5px 0; color:#007bff;">${item.title}</h3>
                <p style="font-size:14px;">${item.desc}</p>
                <button onclick="alert('${item.sol.replace(/\n/g, '\\n')}')" style="background:#f1f1f1; border:none; padding:8px 15px; border-radius:15px; margin-top:5px; width:100%; color:#333;">Показать решение</button>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        container.innerHTML = "<p>Ошибка загрузки базы.</p>";
    }
}

// --- 3. ДИАГНОСТИКА ---
const RU_NAMES = {
    'microwave': 'Микроволновка', 'breadmaker': 'Хлебопечка',
    'multicooker': 'Мультиварка', 'smartphone': 'Смартфон',
    'laptop': 'Ноутбук', 'printer': 'Принтер'
};

async function classifyImage(file) {
    if(!file) return;
    
    const preview = document.getElementById('previewImg');
    const resultText = document.getElementById('detectedText');
    const symptomBox = document.getElementById('symptomBox');
    
    if(preview) preview.src = URL.createObjectURL(file);
    if(resultText) {
        resultText.style.display = 'block';
        resultText.textContent = "Анализ...";
    }

    const fd = new FormData();
    fd.append('file', file);

    try {
        const res = await fetch('/ai/classify', { method: 'POST', body: fd });
        const data = await res.json();
        
        let rawName = data.fault ? data.fault.toLowerCase() : 'unknown';
        let ruName = RU_NAMES[rawName] || rawName;
        currentDevice = ruName;

        if(resultText) {
            resultText.innerHTML = `Вижу: <b>${ruName}</b> <br><small>Точность: ${(data.confidence*100).toFixed(0)}%</small>`;
        }
        if(symptomBox) symptomBox.style.display = 'block';

    } catch(e) {
        if(resultText) resultText.textContent = "Ошибка сервера.";
    }
}

const camInput = document.getElementById('cameraInput');
const galInput = document.getElementById('galleryInput');

if(camInput) camInput.addEventListener('change', e => classifyImage(e.target.files[0]));
if(galInput) galInput.addEventListener('change', e => classifyImage(e.target.files[0]));

// --- 4. ЧАТ (ИСПРАВЛЕНО) ---
async function sendChat() {
    // Используем глобальные переменные, объявленные вверху
    if(!chatIn || !chatOut) return;
    
    const txt = chatIn.value.trim();
    if(!txt) return;
    
    addMsg(txt, 'user');
    chatIn.value = '';
    
    const loader = addMsg('...', 'ai');
    
    try {
        const res = await fetch('/ai/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ question: txt, device_type: currentDevice })
        });
        const data = await res.json();
        loader.innerHTML = data.answer.replace(/\n/g, '<br>');
    } catch(e) {
        loader.textContent = "Ошибка связи.";
    }
}

function addMsg(text, role) {
    if(!chatOut) return;
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.style.cssText = "padding:10px; margin:10px; border-radius:10px; max-width:80%;";
    
    if(role === 'user') {
        div.style.background = "#007bff"; 
        div.style.color = "white"; 
        div.style.marginLeft = "auto";
    } else {
        div.style.background = "#f1f1f1"; 
        div.style.color = "black";
    }
    
    div.innerHTML = text;
    chatOut.appendChild(div);
    chatOut.scrollTop = chatOut.scrollHeight;
    return div;
}

// Теперь переменная sendBtn видна, так как объявлена глобально
if(sendBtn) sendBtn.addEventListener('click', sendChat);

// Отправка по Enter
if(chatIn) {
    chatIn.addEventListener('keypress', e => {
        if(e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChat();
        }
    });
}

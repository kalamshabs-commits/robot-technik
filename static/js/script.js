// 1. Service Worker (Чтобы появилась кнопка "Скачать")
if ('serviceWorker' in navigator) { 
  try { 
    navigator.serviceWorker.register('/static/sw.js')
      .then(() => console.log('SW зарегистрирован'))
      .catch(err => console.error('Ошибка SW:', err));
  } catch(e) { console.log(e); } 
}

// 2. Логика вкладок
const views = Array.from(document.querySelectorAll('.view'));
const tabs = Array.from(document.querySelectorAll('.tabbar .tab'));

function show(id) { 
  views.forEach(v => v.classList.toggle('active', v.id === id)); 
  tabs.forEach(t => t.classList.toggle('active', t.dataset.view === id)); 
}
tabs.forEach(t => t.addEventListener('click', () => show(t.dataset.view)));

// 3. Элементы
const camera = document.getElementById('cameraInput');
const gallery = document.getElementById('galleryInput');
const previewImg = document.getElementById('previewImg');
const detectedText = document.getElementById('detectedText');
const solveBtn = document.getElementById('solveBtn');
const installBtn = document.getElementById('installBtn');
const aiChecklist = document.getElementById('aiChecklist');
const symptomBox = document.getElementById('symptomBox');
const symptomInput = document.getElementById('symptomInput');

let lastDevice = ''; 
const RU = {printer:'Принтер', smartphone:'Смартфон', laptop:'Ноутбук', microwave:'Микроволновка', breadmaker:'Хлебопечка', multicooker:'Мультиварка'};

// 4. Сжатие фото перед отправкой
async function resizeImage(file) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      const canvas = document.createElement('canvas');
      const maxW = 1000; 
      const scale = Math.min(1, maxW / img.width);
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(blob => resolve(new File([blob], 'photo.jpg', {type: 'image/jpeg'})), 'image/jpeg', 0.8);
    };
    img.src = URL.createObjectURL(file);
  });
}

// 5. Отправка фото (Диагностика)
async function classify(file) {
  try {
    file = await resizeImage(file);
    const fd = new FormData();
    fd.append('file', file);

    detectedText.textContent = "Анализирую...";
    detectedText.style.display = 'block';

    const res = await fetch('/ai/classify', { method: 'POST', body: fd });
    
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`Ошибка сервера: ${res.status} ${errText}`);
    }

    const data = await res.json();
    
    previewImg.src = URL.createObjectURL(file);
    lastDevice = data.fault || '';
    window.__lastDeviceType = lastDevice;

    if (lastDevice) {
      detectedText.textContent = `Я вижу: ${RU[lastDevice] || lastDevice}`;
    } else {
      detectedText.textContent = "Не удалось распознать прибор.";
    }
    symptomBox.style.display = 'block';

  } catch (e) {
    console.error(e);
    alert("Ошибка: Не удалось подключиться к серверу. Возможно, модель не загрузилась. Проверьте логи.");
    detectedText.textContent = "Ошибка связи.";
  }
}

// Обработчики кнопок камеры
if(camera) camera.addEventListener('change', e => { if(e.target.files[0]) classify(e.target.files[0]); });
if(gallery) gallery.addEventListener('change', e => { if(e.target.files[0]) classify(e.target.files[0]); });

// 6. Получить решение (Кнопка)
if(solveBtn) solveBtn.addEventListener('click', async () => {
  const problem = symptomInput.value;
  if(!problem) return alert("Напишите проблему!");
  
  solveBtn.disabled = true;
  solveBtn.textContent = "ИИ думает...";
  aiChecklist.innerHTML = "Загрузка...";

  try {
    const payload = {
      question: `Прибор: ${lastDevice}. Проблема: ${problem}. Дай чек-лист решения.`,
      device_type: lastDevice
    };
    const res = await fetch('/ai/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    
    const text = (data.answer || "Нет ответа").replace(/\n/g, '<br>');
    aiChecklist.innerHTML = `<div style="text-align:left; margin-top:10px">${text}</div>`;
    
  } catch(e) {
    aiChecklist.textContent = "Ошибка ИИ.";
  } finally {
    solveBtn.disabled = false;
    solveBtn.textContent = "Получить решение";
  }
});

// 7. ЧАТ
const sendBtn = document.getElementById('sendBtn');
const chatInput = document.getElementById('chatInput');
const chatOut = document.getElementById('chatOut');

async function sendChat() {
  const text = chatInput.value.trim();
  if(!text) return;
  
  chatOut.insertAdjacentHTML('beforeend', `<div class="msg-user">${text}</div>`);
  chatInput.value = '';
  
  const loader = document.createElement('div');
  loader.className = 'msg-ai';
  loader.textContent = '...';
  chatOut.appendChild(loader);
  chatOut.scrollTop = chatOut.scrollHeight;

  try {
    const res = await fetch('/ai/chat', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ question: text, device_type: window.__lastDeviceType })
    });
    const data = await res.json();
    chatOut.removeChild(loader);
    
    const aiText = (data.answer || "Ошибка").replace(/\n/g, '<br>');
    chatOut.insertAdjacentHTML('beforeend', `<div class="msg-ai">${aiText}</div>`);
    chatOut.scrollTop = chatOut.scrollHeight;
  } catch(e) {
    loader.textContent = "Ошибка связи.";
  }
}

if(sendBtn) sendBtn.addEventListener('click', sendChat);

// 8. МИКРОФОН
const micBtn = document.getElementById('micBtn');
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

if(SpeechRecognition && micBtn) {
  const recognition = new SpeechRecognition();
  recognition.lang = 'ru-RU';
  
  micBtn.addEventListener('click', () => {
    try {
      recognition.start();
      micBtn.style.backgroundColor = 'red';
      micBtn.textContent = '👂';
    } catch(e) { console.error(e); }
  });
  
  recognition.addEventListener('result', (e) => {
    const txt = e.results[0][0].transcript;
    chatInput.value = txt;
    micBtn.style.backgroundColor = '';
    micBtn.textContent = '🎙️';
  });
  
  recognition.addEventListener('end', () => {
    micBtn.style.backgroundColor = '';
    micBtn.textContent = '🎙️';
  });
} else if(micBtn) {
  micBtn.style.display = 'none';
}

// 9. Кнопка "Установить" (PWA)
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  if(installBtn) installBtn.style.display = 'block';
});

if(installBtn) installBtn.addEventListener('click', async () => {
  if(deferredPrompt) {
    deferredPrompt.prompt();
    deferredPrompt = null;
    installBtn.style.display = 'none';
  }
});
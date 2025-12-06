if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}

// прелоадер
let __loaderEl=null;function showLoader(){try{if(!__loaderEl){__loaderEl=document.createElement('div');__loaderEl.className='loader';__loaderEl.innerHTML='<div class="spinner"></div>';document.body.appendChild(__loaderEl);}__loaderEl.style.display='flex';}catch{}}
function hideLoader(){try{if(__loaderEl){__loaderEl.style.display='none';}}catch{}}

let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const installBtn = document.createElement('button');
  installBtn.textContent = 'Установить Робот-технолог';
  installBtn.style.position = 'fixed';
  installBtn.style.bottom = '20px';
  installBtn.style.right = '20px';
  installBtn.style.zIndex = '2000';
  installBtn.addEventListener('click', async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    try { await deferredPrompt.userChoice; } catch {}
    deferredPrompt = null;
    installBtn.remove();
  });
  document.body.appendChild(installBtn);
});

const fileInput = document.getElementById('file');
const openBtn = document.getElementById('openCamera');
const statusEl = document.getElementById('status');
const resultEl = document.getElementById('result');
const previewImg = document.getElementById('preview');
const overlay = document.getElementById('overlay');
const chatInput = document.getElementById('chatInput');
const askBtn = document.getElementById('askBtn');
const voiceBtn = document.getElementById('voiceBtn');
const speakBtn = document.getElementById('speakBtn');
const chatOut = document.getElementById('chatOut');
const downloadBtn = document.getElementById('downloadBtn');
const shareBtn = document.getElementById('shareBtn');

const DEVICE_CLASSES = {0:'принтер',1:'смартфон',2:'ноутбук',3:'микроволновка',4:'хлебопечка',5:'мультиварка'};
const FORMS = {
  'принтер': ['принтер', 'принтера', 'принтеров'],
  'смартфон': ['смартфон', 'смартфона', 'смартфонов'],
  'ноутбук': ['ноутбук', 'ноутбука', 'ноутбуков'],
  'микроволновка': ['микроволновка', 'микроволновки', 'микроволновок'],
  'хлебопечка': ['хлебопечка', 'хлебопечки', 'хлебопечек'],
  'мультиварка': ['мультиварка', 'мультиварки', 'мультиварок']
};
function pluralize(name, n){
  const f = FORMS[name] || [name, name, name];
  const mod10 = n % 10, mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return f[0];
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return f[1];
  return f[2];
}

async function classify() {
  try {
    showLoader();
    const f = fileInput.files && fileInput.files[0];
    if (!f) { return; }
    statusEl.textContent = 'Идёт распознавание…';
    resultEl.textContent = '';
    const url = URL.createObjectURL(f);
    previewImg.src = url;
    previewImg.style.display = 'block';
    overlay.style.display = 'none';
    overlay.width = 0; overlay.height = 0;
    const fd = new FormData();
    fd.append('file', f);
    const res = await fetch('/ai/classify', { method: 'POST', body: fd });
    if (!res.ok) { throw new Error('Ошибка сети: ' + res.status); }
    const json = await res.json();

    let ids = [];
    if (Array.isArray(json)) {
      for (const it of json) {
        if (typeof it === 'number') ids.push(it);
        else if (it && typeof it.class === 'number') ids.push(it.class);
        else if (Array.isArray(it?.classes)) ids.push(...it.classes.filter(x=>typeof x==='number'));
      }
    }
    if (typeof json.class === 'number') ids.push(json.class);
    if (Array.isArray(json.classes)) ids.push(...json.classes.filter(x=>typeof x==='number'));
    if (Array.isArray(json.predictions)) ids.push(...json.predictions.map(p=>p.class).filter(x=>typeof x==='number'));

    const counts = {};
    for (const id of ids) {
      const name = DEVICE_CLASSES[id] || `класс ${id}`;
      counts[name] = (counts[name] || 0) + 1;
    }
    let lastDeviceType = '';
    if (Object.keys(counts).length) {
      lastDeviceType = Object.entries(counts).sort((a,b)=>b[1]-a[1])[0][0];
    }
    const pieces = Object.entries(counts).map(([name,count]) => `${count} ${pluralize(name, count)}`);
    const summary = pieces.length ? `Распознано: ${pieces.join(', ')}` : 'Распознано: ничего';

    statusEl.textContent = 'Готово';
    const faultCard = `<div class="card fade-in"><div class="card-title">Вероятная неисправность</div>
      <div><b>${json.fault||'—'}</b></div>
      <div class="chip">${json.reason||''}</div>
      <div class="progress"><div class="bar" id="progressBar"></div></div>
      <div style="margin-top:8px"><b>Шаги:</b><ul id="checklistUI"></ul></div>
    </div>`;
    const summaryList = `<h2>${summary}</h2><ul>${Object.entries(counts).map(([name,count])=>`<li>${name}: ${count}</li>`).join('')}</ul>`;
    resultEl.innerHTML = faultCard + summaryList;
    const steps=(json.checklist||[]);
    const bar=document.getElementById('progressBar');
    const list=document.getElementById('checklistUI');
    let i=0;function next(){ if(i>=steps.length){ bar.style.width='100%'; return;} list.insertAdjacentHTML('beforeend', `<li class="fade-in">${steps[i++]}</li>`); bar.style.width=((i/Math.max(steps.length,1))*100)+'%'; setTimeout(next, 350);} next();
    window.__lastDeviceType = lastDeviceType;
    window.__lastDetections = (json.diagnosisChecklist || []).slice();
    window.__lastBoxes = (json.suspectNodes || []).map(x=>x && x.bbox).filter(Boolean);

    previewImg.onload = ()=>{
      try{
        overlay.style.display = 'block';
        overlay.width = previewImg.clientWidth;
        overlay.height = previewImg.clientHeight;
        const ctx = overlay.getContext('2d');
        ctx.clearRect(0,0,overlay.width, overlay.height);
        const natW = previewImg.naturalWidth || overlay.width;
        const natH = previewImg.naturalHeight || overlay.height;
        const sx = overlay.width / natW;
        const sy = overlay.height / natH;
        ctx.strokeStyle = '#e53935';
        ctx.lineWidth = 2;
        const boxes=(window.__lastBoxes||[]);
        let i=0;function drawNext(){ if(i>=boxes.length) return; const b=boxes[i++]; const [x1,y1,x2,y2]=b; ctx.strokeRect(x1*sx,y1*sy,(x2-x1)*sx,(y2-y1)*sy); setTimeout(drawNext,80);} drawNext();
      }catch(e){ overlay.style.display='none'; }
    };

    await generateChecklistAuto(lastDeviceType, window.__lastDetections||[]);
  } catch (e) {
    statusEl.textContent = 'Ошибка';
    alert(e.message || 'Ошибка запроса');
  }
  finally{ hideLoader(); }
}

openBtn.addEventListener('click', ()=> fileInput.click());
fileInput.addEventListener('change', classify);

window.lastAnswer = '';
window.lastChecklistText = '';
window.lastBrand = window.lastBrand || '';
async function askAI(){
  const q = (chatInput.value || '').trim();
  if(!q) return;
  chatOut.innerHTML = '<div class="skeleton" style="height:48px"></div>';
  try{
    const payload = {question:q, device_type: window.__lastDeviceType || '', detected_objects: (window.__lastDetections||[]) };
    showLoader();
    const res = await fetch('/ai/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    if(!res.ok) throw new Error('Ошибка сети: '+res.status);
    const json = await res.json();
    window.lastAnswer = json.answer || '';
    const aiLines = (window.lastAnswer || '').split(/\r?\n/).map(s=>s.trim()).filter(s=>s);
    const aiItems = aiLines.length ? aiLines : [window.lastAnswer || ''];
    chatOut.innerHTML = '<ul id="chatList"></ul>';
    const ul = document.getElementById('chatList');
    let ci=0; function reveal(){ if(ci>=aiItems.length) return; ul.insertAdjacentHTML('beforeend', `<li class="fade-in">${aiItems[ci++]}</li>`); setTimeout(reveal, 300);} reveal();
    const dt = window.__lastDeviceType || '';
    const now = new Date();
    const dateText = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
    const body = aiItems.map((s,i)=>`${i+1}. ${s}`).join('\n');
    window.lastChecklistText = `ЧЕК-ЛИСТ\nПрибор: ${dt} ${window.lastBrand}\nДата: ${dateText}\n${body}`;
    downloadBtn.style.display = 'inline-block';
    if(shareBtn) shareBtn.style.display = 'inline-block';
  }catch(e){
    chatOut.textContent = 'Ошибка: '+(e.message||'запрос');
  } finally{ hideLoader(); }
}
askBtn.addEventListener('click', askAI);

function speakText(t){
  if(!('speechSynthesis' in window)) return;
  const u = new SpeechSynthesisUtterance(t);
  u.lang = 'ru-RU';
  const voices = speechSynthesis.getVoices();
  const ru = voices.find(v=>/ru/i.test(v.lang));
  if(ru) u.voice = ru;
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}
speakBtn.addEventListener('click', ()=>{ if(window.lastAnswer) speakText(window.lastAnswer); });

let rec = null; let recording = false;
function initRec(){
  const R = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!R) return null;
  const r = new R();
  r.lang = 'ru-RU';
  r.interimResults = false;
  r.maxAlternatives = 1;
  r.onresult = (e)=>{
    const t = e.results[0] && e.results[0][0] && e.results[0][0].transcript || '';
    chatInput.value = t;
    askAI();
  };
  r.onend = ()=>{ recording = false; voiceBtn.textContent = '🎙️ Голос'; };
  return r;
}
voiceBtn.addEventListener('click', ()=>{
  if(!rec) rec = initRec();
  if(!rec) { alert('Голос недоступен в этом браузере'); return; }
  if(!recording){ recording = true; voiceBtn.textContent = '⏹️ Стоп'; rec.start(); } else { recording = false; voiceBtn.textContent = '🎙️ Голос'; rec.stop(); }
});

function downloadChecklist(){
  const dt = window.__lastDeviceType || 'прибор';
  const text = window.lastChecklistText || (window.lastAnswer || '');
  const blob = new Blob([text], {type: 'text/plain'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `робот-технолог_чек-лист_${dt}_${Date.now()}.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
downloadBtn.addEventListener('click', downloadChecklist);

function shareChecklist(){
  const dt = window.__lastDeviceType || 'прибор';
  const text = window.lastChecklistText || (window.lastAnswer || '');
  if(navigator.share){ navigator.share({title:`Чек-лист — ${dt}`, text}); }
  else{ try{ navigator.clipboard.writeText(text); alert('Чек-лист скопирован в буфер обмена'); }catch(e){ alert('Скопируйте вручную: '+text.slice(0,200)+'...'); } }
}
if(shareBtn){ shareBtn.addEventListener('click', shareChecklist); }

async function generateChecklistAuto(deviceType, detected){
  try{
    const q = `Сформируй пошаговый чек-лист ремонта для приборов типа "${deviceType}" с учётом распознанных деталей: ${detected.join(', ')}. Дай краткие безопасные шаги.`;
    showLoader();
    const res = await fetch('/ai/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({question: q, device_type: deviceType || '', detected_objects: detected || []})});
    if(!res.ok) return;
    const json = await res.json();
    const now = new Date();
    const dateText = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
    const checklistLines = (json.answer || '').split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
    const body = (checklistLines.length ? checklistLines : [json.answer || '']).map((s,i)=>`${i+1}. ${s}`).join('\n');
    window.lastChecklistText = `ЧЕК-ЛИСТ\nПрибор: ${deviceType} ${window.lastBrand}\nДата: ${dateText}\n${body}`;
    downloadBtn.style.display = 'inline-block';
  }catch(e){}
  finally{ hideLoader(); }
}

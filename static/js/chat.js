(()=>{
const openAdvisor = document.getElementById('advisorLink');
const advisorModal = document.getElementById('advisorModal');
const closeAdvisor = document.getElementById('closeAdvisor');
const advisorHistory = document.getElementById('advisorHistory');
const advisorInput = document.getElementById('advisorInput');
const advisorSend = document.getElementById('advisorSend');
const advisorVoice = document.getElementById('advisorVoice');
const advisorClear = document.getElementById('advisorClear');
const advisorDownload = document.getElementById('advisorDownload');

let advisorData = [];
try{ const raw = localStorage.getItem('advisorHistory'); if(raw){ advisorData = JSON.parse(raw) || []; } }catch(e){}

function renderAdvisor(){
  advisorHistory.innerHTML = advisorData.map(m=>`<div class="msg ${m.role}"><b>${m.role==='user'?'User':'Assistant'}:</b> ${m.text}</div>`).join('');
  advisorHistory.scrollTop = advisorHistory.scrollHeight;
  try{ localStorage.setItem('advisorHistory', JSON.stringify(advisorData)); }catch(e){}
}

function openAdv(){ advisorModal.setAttribute('aria-hidden','false'); advisorModal.style.display='block'; renderAdvisor(); }
function closeAdv(){ advisorModal.setAttribute('aria-hidden','true'); advisorModal.style.display='none'; }
openAdvisor.addEventListener('click', (e)=>{ if(e.metaKey||e.ctrlKey) return; e.preventDefault(); openAdv(); });
closeAdvisor.addEventListener('click', closeAdv);
document.addEventListener('keydown', (e)=>{ if(e.key==='Escape') closeAdv(); });

let modalFocusables=[];
function trapFocus(e){
  if(advisorModal.style.display!=='block') return;
  if(e.key!=='Tab') return;
  if(!modalFocusables.length){
    modalFocusables=Array.from(advisorModal.querySelectorAll('button, [href], input, textarea, [tabindex]:not([tabindex="-1"])')).filter(el=>!el.disabled);
  }
  const idx=modalFocusables.indexOf(document.activeElement);
  if(e.shiftKey){
    if(idx<=0){ e.preventDefault(); modalFocusables[modalFocusables.length-1].focus(); }
  } else {
    if(idx===modalFocusables.length-1){ e.preventDefault(); modalFocusables[0].focus(); }
  }
}
document.addEventListener('keydown', trapFocus);
advisorInput.addEventListener('keydown', (e)=>{ if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendAdvisor(); } });
openAdvisor.addEventListener('click', ()=>{ setTimeout(()=>{ try{ (advisorInput||advisorSend||closeAdvisor).focus(); }catch(e){} }, 0); });

async function sendAdvisor(){
  const q = (advisorInput.value||'').trim();
  if(!q) return;
  advisorData.push({role:'user', text:q});
  renderAdvisor();
  advisorSend.disabled = true;
  try{
    const history = advisorData.map(x=>({role:x.role, text:x.text}));
    const payload = {question:q, device_type: window.__lastDeviceType || '', brand: (window.lastBrand||''), chat_history: history};
    const res = await fetch('/ai/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    const json = await res.json();
    const ans = json.answer || '';
    advisorData.push({role:'assistant', text: ans});
    renderAdvisor();
    advisorInput.value = '';
  }catch(e){
    advisorData.push({role:'assistant', text: 'Ошибка запроса'});
    renderAdvisor();
  }finally{
    advisorSend.disabled = false;
  }
}
advisorSend.addEventListener('click', sendAdvisor);
advisorClear.addEventListener('click', ()=>{ advisorData = []; renderAdvisor(); });
const advisorClear2 = document.getElementById('advisorClear2');
if(advisorClear2){ advisorClear2.addEventListener('click', ()=>{ try{ localStorage.removeItem('advisorHistory'); advisorData=[]; renderAdvisor(); }catch(e){} }); }

advisorDownload.addEventListener('click', ()=>{
  const dt = window.__lastDeviceType || 'прибор';
  const now = new Date();
  const dateText = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
  let text = `ЧАТ-СОВЕТНИК\nПрибор: ${dt} ${(window.lastBrand||'')}\nДата: ${dateText}\n--------------------------------\n`;
  for(const m of advisorData){ text += `${m.role==='user'?'User':'Assistant'}: ${m.text}\n`; }
  const blob = new Blob([text], {type: 'text/plain'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `робот-технолог_чат_${dt}_${Date.now()}.txt`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
});

let rec2 = null; let recOn = false;
function initRec2(){
  const R = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(!R) return null;
  const r = new R();
  r.lang = 'ru-RU';
  r.interimResults = false;
  r.maxAlternatives = 1;
  r.onresult = (e)=>{
    const t = e.results[0] && e.results[0][0] && e.results[0][0].transcript || '';
    advisorInput.value = t;
    sendAdvisor();
  };
  r.onend = ()=>{ recOn = false; advisorVoice.textContent = '🎙️ Голос'; };
  return r;
}
advisorVoice.addEventListener('click', ()=>{
  if(!rec2) rec2 = initRec2();
  if(!rec2){ alert('Голос недоступен в этом браузере'); return; }
  if(!recOn){ recOn = true; advisorVoice.textContent = '⏹️ Стоп'; rec2.start(); } else { recOn = false; advisorVoice.textContent = '🎙️ Голос'; rec2.stop(); }
});
})();

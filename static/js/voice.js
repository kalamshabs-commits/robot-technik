let rec=null;let on=false;
function init(){
  const R=window.SpeechRecognition||window.webkitSpeechRecognition; if(!R) return null; const r=new R();
  r.lang='ru-RU';r.interimResults=false;r.maxAlternatives=1;
  r.onresult=(e)=>{ const t=e.results[0]&&e.results[0][0]&&e.results[0][0].transcript||''; document.getElementById('voiceText').value=t; };
  r.onend=()=>{ on=false; document.getElementById('startVoice').textContent='🎙️ Начать'; };
  return r;
}
document.getElementById('startVoice').addEventListener('click',()=>{
  if(!rec) rec=init(); if(!rec){ alert('Голос недоступен'); return; }
  if(!on){ on=true; document.getElementById('startVoice').textContent='⏹️ Стоп'; rec.start(); } else { on=false; document.getElementById('startVoice').textContent='🎙️ Начать'; rec.stop(); }
});
document.getElementById('sendToChat').addEventListener('click',async()=>{
  const q=(document.getElementById('voiceText').value||'').trim(); if(!q) return;
  document.getElementById('answer').textContent='ИИ думает…';
  try{
    const res=await fetch('/ai/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:q,device_type:''})});
    const json=await res.json();
    document.getElementById('answer').textContent=json.answer||'';
  }catch(e){ document.getElementById('answer').textContent='Ошибка'; }
});

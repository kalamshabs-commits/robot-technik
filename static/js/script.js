(() => {
  // 1. Service Worker для PWA
  if ('serviceWorker' in navigator) { 
    try{ navigator.serviceWorker.register('/static/sw.js') }catch(e){console.log('SW fail',e)} 
  }

  // 2. Логика вкладок (Табов)
  const views = Array.from(document.querySelectorAll('.view'))
  const tabs = Array.from(document.querySelectorAll('.tabbar .tab'))
  function show(id){ 
    views.forEach(v=>v.classList.toggle('active', v.id===id)); 
    tabs.forEach(t=>t.classList.toggle('active', t.dataset.view===id)); 
  }
  tabs.forEach(t=> t.addEventListener('click', ()=> show(t.dataset.view)))
  show('home')

  // 3. Переменные и элементы
  let lastDevice = ''
  const camera = document.getElementById('cameraInput')
  const gallery = document.getElementById('galleryInput')
  const resultBox = document.getElementById('resultBox')
  const previewImg = document.getElementById('previewImg')
  const aiChecklist = document.getElementById('aiChecklist')
  const detectedText = document.getElementById('detectedText')
  const symptomBox = document.getElementById('symptomBox')
  const symptomInput = document.getElementById('symptomInput')
  const solveBtn = document.getElementById('solveBtn')
  const printBtn = document.getElementById('printBtn')
  const installBtn = document.getElementById('installBtn')
  const deviceFallback = document.getElementById('deviceFallback')
  
  // Словарь
  const RU = {printer:'Принтер', smartphone:'Смартфон', laptop:'Ноутбук', microwave:'Микроволновка', breadmaker:'Хлебопечка', multicooker:'Мультиварка'}

  // 4. Сжатие картинки
  async function resizeImage(file){
    return new Promise((resolve,reject)=>{
      const img = new Image()
      img.onload = ()=>{
        const maxW = 1024
        const scale = Math.min(1, maxW / img.width)
        const w = Math.round(img.width * scale)
        const h = Math.round(img.height * scale)
        const canvas = document.createElement('canvas')
        canvas.width = w; canvas.height = h
        const ctx = canvas.getContext('2d')
        ctx.drawImage(img, 0, 0, w, h)
        canvas.toBlob(b=> b? resolve(new File([b], 'photo.jpg', {type:'image/jpeg'})): reject(new Error('Blob error')), 'image/jpeg', 0.7)
      }
      img.onerror = reject
      img.src = URL.createObjectURL(file)
    })
  }

  // 5. Отрисовка чек-листа
  function renderChecklist(lines, targetElement = aiChecklist){
    const items = lines && lines.length ? lines : []
    const html = '<ul class="checklist">'+ items.map(s=>{
      let text = s.replace(/^[-\*•]\s*/, '').trim()
      return `<li><label><input type="checkbox"> <span>${text}</span></label></li>`
    }).join('') + '</ul>'
    targetElement.innerHTML = html
    resultBox.style.display = 'block'
  }

  // 6. Классификация (YOLO)
  async function classify(file){
    try{ file = await resizeImage(file) }catch(e){console.error(e)}
    
    const fd = new FormData()
    fd.append('file', file)
    
    const loader = document.createElement('div'); loader.className='loader'; loader.innerHTML='<div class="spinner"></div>'; document.body.appendChild(loader)
    
    try{
      const res = await fetch('/ai/classify', {method:'POST', body: fd})
      if(!res.ok) throw new Error('Server Error')
      const j = await res.json()
      
      const url = URL.createObjectURL(file)
      previewImg.src = url
      
      lastDevice = j.fault || ''
      window.__lastDeviceType = lastDevice
      
      if(lastDevice){ 
        detectedText.textContent = `Я вижу: ${RU[lastDevice]||lastDevice}`
        detectedText.style.display='inline-block' 
      } else {
        detectedText.textContent = 'Прибор не распознан, но я попробую помочь.'
        detectedText.style.display='inline-block'
      }
      
      symptomBox.style.display='block'
      aiChecklist.innerHTML = ''
      
    }catch(e){ 
      detectedText.textContent = 'Сеть недоступна. Выберите прибор вручную:'
      detectedText.style.display='inline-block'
      aiChecklist.innerHTML = ''
      symptomBox.style.display = 'none'
      if(deviceFallback){
        deviceFallback.innerHTML = ''
        const devices = ['multicooker','smartphone','laptop','printer','microwave','breadmaker']
        devices.forEach(k=>{
          const b = document.createElement('button')
          b.className='chip'
          b.textContent=RU[k]||k
          b.addEventListener('click', ()=>{
            lastDevice = k
            window.__lastDeviceType = k
            detectedText.textContent = `Я вижу: ${RU[k]||k}`
            symptomBox.style.display='block'
            deviceFallback.style.display='none'
          })
          deviceFallback.appendChild(b)
        })
        deviceFallback.style.display = 'flex'
      }
      resultBox.style.display='block'
    }
    finally{ 
      if(loader.parentNode) document.body.removeChild(loader) 
    }
  }

  camera.addEventListener('change', e=>{ const f=e.target.files[0]; if(f) classify(f) })
  gallery.addEventListener('change', e=>{ const f=e.target.files[0]; if(f) classify(f) })
  if(printBtn) printBtn.addEventListener('click', ()=> window.print())

  // 7. Получить решение (DeepSeek)
  async function solve(){
    const problem = (symptomInput.value||'').trim()
    const dt = lastDevice || 'Неизвестный прибор'
    
    if(!problem) {
      alert('Пожалуйста, опишите проблему')
      return
    }
    
    aiChecklist.innerHTML = '<div class="skeleton" style="height:48px"></div><div class="skeleton" style="height:48px"></div>'
    solveBtn.disabled = true; solveBtn.textContent = 'Думаю...'
    
    try{
      const q = `Устройство: ${RU[dt]||dt}. Проблема: ${problem}. Составь пошаговый чек-лист ремонта.`
      const payload = {question: q, device_type: dt}
      
      const res = await fetch('/ai/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
      const j = await res.json()
      
      let text = j.answer || ''
      text = text.replace(/^.*?(?:Вот|Предлагаю|Чек-лист).*?:/i, '')
      
      const lines = text.split(/\n/).map(s=>s.trim()).filter(s => s.length > 3)
      renderChecklist(lines)
      if(printBtn) printBtn.style.display = 'inline-block'
      
    }catch(e){ 
      // Офлайн фоллбэк
      try{
        const kbRes = await fetch('/knowledge')
        const KB = await kbRes.json()
        const faults = (KB[lastDevice]&&KB[lastDevice].common_faults)||[]
        const match = faults.find(f=>{
          const kws = f.symptom_keywords||[]
          return kws.some(kw=> problem.toLowerCase().includes(String(kw||'').toLowerCase()))
        })
        const lines = match ? (match.steps||[]) : []
        if(lines.length){ renderChecklist(lines) } else { aiChecklist.innerHTML = '<div style="color:red">Ошибка ИИ. Проверьте интернет.</div>' }
      }catch(_){ aiChecklist.innerHTML = '<div style="color:red">Ошибка ИИ. Проверьте интернет.</div>' }
    } finally {
      solveBtn.disabled = false; solveBtn.textContent = 'Получить решение'
    }
  }
  solveBtn.addEventListener('click', solve)

  // 8. PWA Install
  let deferredPrompt = null
  window.addEventListener('beforeinstallprompt', (e)=>{
    e.preventDefault(); deferredPrompt = e; 
    if(installBtn) installBtn.style.display = 'inline-block'
  })
  if(installBtn) installBtn.addEventListener('click', async ()=>{
    if(!deferredPrompt) return
    deferredPrompt.prompt()
    try{ await deferredPrompt.userChoice }catch{}
    installBtn.style.display = 'none'; deferredPrompt = null
  })

  // 9. ЧАТ
  const chatInput = document.getElementById('chatInput')
  const chatOut = document.getElementById('chatOut')
  const sendBtn = document.getElementById('sendBtn')
  const micBtn = document.getElementById('micBtn')
  
  async function sendChat(){
    const q = (chatInput.value||'').trim()
    if(!q) return
    
    chatOut.insertAdjacentHTML('beforeend', `<div class="msg-user">${q}</div>`)
    chatInput.value = ''
    
    const loader = document.createElement('div'); loader.className='msg-ai skeleton'; loader.textContent='...'; 
    chatOut.appendChild(loader)
    chatOut.scrollTop = chatOut.scrollHeight
    
    try{
      const payload = {question:q, device_type: window.__lastDeviceType || ''}
      const res = await fetch('/ai/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)})
      const j = await res.json()
      
      chatOut.removeChild(loader)
      const answerHtml = (j.answer||'').replace(/\n/g, '<br>')
      chatOut.insertAdjacentHTML('beforeend', `<div class="msg-ai">${answerHtml}</div>`)
      chatOut.scrollTop = chatOut.scrollHeight
      
    }catch(e){ loader.textContent = 'Ошибка связи' }
  }
  sendBtn.addEventListener('click', sendChat)

  // ===============================================
  // 10. ГОЛОСОВОЙ ВВОД (ИСПРАВЛЕННАЯ ВЕРСИЯ)
  // ===============================================
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (SpeechRecognition && micBtn) {
      const recognition = new SpeechRecognition();
      recognition.lang = 'ru-RU';     // Язык - Русский
      recognition.interimResults = false; 

      micBtn.addEventListener('click', () => {
          // Если уже слушаем - можно остановить (опционально) или просто игнорировать
          if (micBtn.classList.contains('recording')) {
             recognition.stop();
             return;
          }
          
          try {
              recognition.start();
              micBtn.classList.add('recording'); // Для CSS стилей
              micBtn.textContent = "👂 Слушаю..."; 
              micBtn.style.backgroundColor = "#d32f2f"; // Красный цвет
              micBtn.style.color = "white";
          } catch (e) {
              console.error("Ошибка запуска микрофона:", e);
          }
      });

      recognition.addEventListener('result', (event) => {
          const text = event.results[0][0].transcript;
          chatInput.value = text; // Вставляем текст
          
          // Возвращаем кнопку в исходное состояние
          resetMicBtn();
      });

      recognition.addEventListener('end', () => {
          resetMicBtn();
      });

      recognition.addEventListener('error', (event) => {
          console.log("Ошибка микрофона: " + event.error);
          resetMicBtn();
          if (event.error === 'not-allowed') {
              alert("Пожалуйста, разрешите доступ к микрофону в настройках.");
          }
      });

      function resetMicBtn() {
          micBtn.classList.remove('recording');
          micBtn.textContent = "🎙️";
          micBtn.style.backgroundColor = ""; 
          micBtn.style.color = "";
      }

  } else {
      console.log("Ваш браузер не поддерживает голосовой ввод");
      if(micBtn) micBtn.style.display = "none";
  }

  // 11. БАЗА ЗНАНИЙ
  let KB = null
  const kbFilters = document.getElementById('kbFilters')
  const kbList = document.getElementById('kbList')
  
  function renderKbList(filter){
    kbList.innerHTML = ''
    if(!KB) return
    const keys = Object.keys(KB)
    const devices = filter && filter!=='all' ? [filter] : keys
    const items = []
    
    for(const d of devices){
      const deviceName = RU[d] || KB[d].name || d
      const faults = (KB[d]&&KB[d].common_faults)||[]
      const faultsArr = Array.isArray(faults) ? faults : Object.entries(faults).map(([k,v])=>({title:k, ...v}))
      for(const f of faultsArr){ items.push({device:deviceName, fault:f}) }
    }
    
    if(items.length === 0) { kbList.innerHTML = '<div style="padding:20px; color:#666">Ничего не найдено</div>'; return }

    for(const it of items){
      const title = it.fault.title || 'Неисправность'
      const solution = it.fault.solution || ''
      const steps = it.fault.steps || []
      
      const el = document.createElement('div')
      el.className = 'kb-card'
      
      let stepsHtml = ''
      if(steps.length) stepsHtml = '<ul>'+steps.map(s=>`<li>${s}</li>`).join('')+'</ul>'
      
      el.innerHTML = `
        <div class="kb-header"><span class="kb-device-tag">${it.device}</span><div class="kb-title">${title}</div></div>
        <div class="kb-body" style="display:none"><div class="kb-solution">${solution}</div>${stepsHtml}</div>
        <div class="kb-actions"><button class="btn-fix">Как починить?</button></div>`
        
      const btn = el.querySelector('.btn-fix')
      const body = el.querySelector('.kb-body')
      btn.addEventListener('click', ()=> {
          const isOpen = body.style.display !== 'none'
          body.style.display = isOpen ? 'none' : 'block'
          btn.textContent = isOpen ? 'Как починить?' : 'Свернуть'
      })
      kbList.appendChild(el)
    }
  }

  function renderKbFilters(){
    kbFilters.innerHTML = ''
    const btnAll = document.createElement('button'); btnAll.className='chip active'; btnAll.textContent='Все'; 
    btnAll.addEventListener('click', (e)=>{
        document.querySelectorAll('.kb-filters .chip').forEach(c=>c.classList.remove('active')); e.target.classList.add('active'); renderKbList('all')
    }); 
    kbFilters.appendChild(btnAll)
    
    for(const k of ['multicooker','smartphone','laptop','printer','microwave','breadmaker']){
      const b = document.createElement('button'); b.className='chip'; b.textContent=RU[k]; 
      b.addEventListener('click', (e)=>{
          document.querySelectorAll('.kb-filters .chip').forEach(c=>c.classList.remove('active')); e.target.classList.add('active'); renderKbList(k)
      }); 
      kbFilters.appendChild(b)
    }
  }

  async function initKB(){ 
      try{ const res=await fetch('/knowledge'); KB=await res.json(); renderKbFilters(); renderKbList('all') }catch(e){} 
  }

  initKB()

})();

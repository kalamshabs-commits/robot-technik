async function loadKB(){
  const res=await fetch('/knowledge',{headers:{'Accept':'application/json'}});
  return await res.json();
}

(async()=>{
  const kb=document.getElementById('kb');
  const sentinel=document.getElementById('kbSentinel');
  const search=document.getElementById('search');
  const filterDevice=document.getElementById('filterDevice');
  const filterBrand=document.getElementById('filterBrand');
  const sortBy=document.getElementById('sortBy');
  kb.innerHTML='<div class="skeleton" style="height:80px;margin:8px 0"></div><div class="skeleton" style="height:80px;margin:8px 0"></div>';
  const raw=await loadKB();

  const all=[];
  for(const section of Object.values(raw||{})){
    if(Array.isArray(section)) all.push(...section); else if(typeof section==='object'){ for(const arr of Object.values(section)){ all.push(...arr); } }
  }
  const devices=new Set();
  const brands=new Set();
  for(const i of all){
    const d=(i.device_type||'').toLowerCase();
    const b=(i.brand||'').toLowerCase();
    if(d) devices.add(d); if(b) brands.add(b);
  }
  for(const d of Array.from(devices).sort()){ const o=document.createElement('option'); o.value=d; o.textContent=d; filterDevice.appendChild(o); }
  for(const b of Array.from(brands).sort()){ const o=document.createElement('option'); o.value=b; o.textContent=b; filterBrand.appendChild(o); }

  let filtered=[]; let idx=0; const BATCH=20; let observer=null; let lastQuery=''; let lastDev=''; let lastBrand=''; let lastSort='pop';

  function scorePopularity(i){ return Number(i.popularity||i.pop||0); }
  function scoreTime(i){ const a=Number(i.time_min||0), b=Number(i.time_max||0); if(a&&b) return (a+b)/2; const t=(i.estimated_time||'').match(/\d+/g); if(t) return Number(t[0]); return 0; }
  function normalizeTitle(s){ return String(s||'').toLowerCase(); }

  function applyFilters(){
    const q=normalizeTitle(search.value);
    const dev=(filterDevice.value||'').toLowerCase();
    const br=(filterBrand.value||'').toLowerCase();
    const sort=sortBy.value||'pop';
    lastQuery=q; lastDev=dev; lastBrand=br; lastSort=sort;
    filtered=all.filter(i=>{
      const t=normalizeTitle(JSON.stringify(i));
      if(q && !t.includes(q)) return false;
      if(dev && normalizeTitle(i.device_type)!==dev) return false;
      if(br && normalizeTitle(i.brand)!==br) return false;
      return true;
    });
    if(sort==='pop') filtered.sort((a,b)=>scorePopularity(b)-scorePopularity(a));
    else if(sort==='time') filtered.sort((a,b)=>scoreTime(a)-scoreTime(b));
    else filtered.sort((a,b)=>normalizeTitle(a.title).localeCompare(normalizeTitle(b.title)));
    idx=0; kb.innerHTML=''; renderNext(); if(observer) observer.disconnect(); observer=new IntersectionObserver(entries=>{ for(const en of entries){ if(en.isIntersecting) renderNext(); } }); observer.observe(sentinel);
  }

  function renderCard(i){
    const tags=(i.tags||i.symptoms||[]);
    const risks=(i.risks||[]);
    const time=i.time_min&&i.time_max?`${i.time_min}-${i.time_max} мин`:(i.estimated_time||'');
    const pop=scorePopularity(i);
    return `<div class="card fade-in">
      <div class="card-title">${i.title||'—'}</div>
      <div>${tags.map(t=>`<span class="chip">${t}</span>`).join('')}</div>
      ${time?`<div class="time" style="margin-top:6px">⏱ ${time}</div>`:''}
      ${pop?`<div style="margin-top:6px;color:#0d47a1">★ Популярность: ${pop}</div>`:''}
      ${risks.length?`<div class="risk" style="margin-top:6px">⚠ ${risks.join(', ')}</div>`:''}
      <ul style="margin-top:8px">${(i.steps||[]).map(s=>`<li>${s}</li>`).join('')}</ul>
    </div>`;
  }

  function renderNext(){
    const end=Math.min(idx+BATCH, filtered.length);
    const frag=[];
    for(let i=idx;i<end;i++){ frag.push(renderCard(filtered[i])); }
    kb.insertAdjacentHTML('beforeend', frag.join(''));
    idx=end;
  }

  search.addEventListener('input', applyFilters);
  filterDevice.addEventListener('change', applyFilters);
  filterBrand.addEventListener('change', applyFilters);
  sortBy.addEventListener('change', applyFilters);
  applyFilters();
})();

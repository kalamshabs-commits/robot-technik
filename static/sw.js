const CACHE_NAME='robot-technician-v7';
const ASSETS=['/','/index.html','/style.css','/manifest.json','/sw.js','/chat','/photo','/voice','/about','/knowledge.html','/js/main.js','/js/chat.js','/js/knowledge.js','/js/voice.js','/js/script.js','/static/icons/robot-technik.png'];
const OFFLINE_HTML='<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Нет интернета — Робот-техник</title><style>body{font-family:system-ui,Arial;padding:24px}h1{font-size:20px}p{color:#444}</style></head><body><h1>Нет интернета</h1><p>Проверьте соединение и попробуйте снова.</p><p><a href="/">На главную</a></p></body></html>';
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE_NAME).then(c=>c.addAll(ASSETS)))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(keys=>Promise.all(keys.map(k=>k!==CACHE_NAME&&caches.delete(k)))).then(()=>self.clients.claim()))});
self.addEventListener('fetch',e=>{
  const req = e.request;
  const url = new URL(req.url);
  // Не перехватываем API/POST/загрузки
  if(req.method !== 'GET') return;
  // Кэш для статических ассетов
  if(url.origin===location.origin && ASSETS.includes(url.pathname)){
    e.respondWith(caches.match(req));
    return;
  }
  // ТОЛЬКО для навигации отдаём offline HTML
  if(req.mode==='navigate'){
    e.respondWith(
      fetch(req).catch(()=>new Response(OFFLINE_HTML,{headers:{'Content-Type':'text/html; charset=utf-8'}}))
    );
    return;
  }
  // Для прочих GET — сеть, при ошибке ничего не ломаем
});

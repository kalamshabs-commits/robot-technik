const CACHE_NAME = 'robot-tech-vfinal';
const ASSETS = [
  '/',                     // Главная страница
  '/static/style.css',     // Стили
  '/static/js/script.js',  // Твой главный скрипт
  '/static/manifest.json', // Манифест
  '/static/icons/robot-technik.png' // Иконка
];

// Установка (Кэшируем файлы)
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(ASSETS))
      .catch(err => console.error("Ошибка кэширования:", err))
  );
});

// Активация (Чистим старый кэш)
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.map(key => {
        if (key !== CACHE_NAME) return caches.delete(key);
      })
    ))
  );
});

// Работа офлайн
self.addEventListener('fetch', event => {
  // Игнорируем POST запросы (ИИ и диагностика)
  if (event.request.method !== 'GET') return;

  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Если есть в кэше — отдаем, если нет — идем в сеть
        return response || fetch(event.request);
      })
      .catch(() => {
        // Если и сети нет, и в кэше нет — ничего не делаем (или можно вернуть offline.html)
      })
  );
});
/* BrianRAG Service Worker — basic offline caching */
const CACHE = 'brianrag-v1';
const STATIC_ASSETS = [
  '/',
  '/styles/main.css',
  '/js/app.js',
  '/Brian.png',
];

self.addEventListener('install', evt => {
  evt.waitUntil(
    caches.open(CACHE).then(cache => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', evt => {
  evt.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', evt => {
  if (evt.request.method !== 'GET') return;
  evt.respondWith(
    caches.match(evt.request).then(cached =>
      cached || fetch(evt.request).then(resp => {
        if (resp.ok && evt.request.url.startsWith(self.location.origin)) {
          const clone = resp.clone();
          caches.open(CACHE).then(cache => cache.put(evt.request, clone));
        }
        return resp;
      }).catch(() => cached || new Response('Offline', { status: 503 }))
    )
  );
});

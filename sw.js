// Auto-generated: updates on every deploy to force SW refresh
const VERSION = 'v20260912-191133';
const CACHE = 'portfolio-' + VERSION;
const OFFLINE_URL = 'index.html';

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k.startsWith('portfolio-') && k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== location.origin) return;

  // Version probes must always reach the network and must never be cached:
  // they are how open pages learn a new deploy exists.
  if (url.searchParams.has('vcheck')) {
    event.respondWith(fetch(request));
    return;
  }
  
  if (request.mode === 'navigate') {
    event.respondWith(
      // cache:'reload' bypasses the browser HTTP cache (Pages sends
      // max-age=600). A plain fetch() would serve stale HTML for 10 minutes
      // after every deploy, so first loads would run old code.
      fetch(request.url, { cache: 'reload' })
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
          return response;
        })
        .catch(() => caches.match(request).then((cached) => cached || caches.match(OFFLINE_URL)))
    );
    return;
  }
  
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request).then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(request, copy));
        return response;
      }).catch(() => cached);
      return cached || network;
    })
  );
});

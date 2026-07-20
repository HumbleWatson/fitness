const VERSION = new URL(self.location).searchParams.get('v') || 'v1';
const CACHE_NAME = 'fitness-' + VERSION;
const ASSETS = [
    '/',
    '/index.html',
    '/stats.html',
    '/diet.html',
    '/manifest.json',
    '/favicon.ico',
    '/favicon.png',
    '/icon-180.png',
    '/icon-192.png',
    '/icon-512.png',
    '/icon.svg'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS).catch(() => {}))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => 
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // API: network only, offline fallback
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request).catch(() => 
                new Response(JSON.stringify({error: 'offline'}), {
                    headers: {'Content-Type': 'application/json'}
                })
            )
        );
        return;
    }

    // HTML navigation: network-first, cache fallback
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request).catch(() => caches.match(request))
        );
        return;
    }

    // Static assets: cache-first
    event.respondWith(
        caches.match(request).then(r => r || fetch(request))
    );
});

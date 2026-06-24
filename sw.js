const VERSION = new URL(self.location).searchParams.get('v') || 'v1';
const CACHE_NAME = 'fitness-' + VERSION;
const ASSETS = [
    '/',
    '/index.html',
    '/stats.html',
    '/manifest.json'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => 
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    if (event.request.url.includes('/api/')) {
        event.respondWith(
            fetch(event.request).catch(() => 
                new Response(JSON.stringify({error: 'offline'}), {
                    headers: {'Content-Type': 'application/json'}
                })
            )
        );
    } else {
        event.respondWith(
            caches.match(event.request).then(response => response || fetch(event.request))
        );
    }
});

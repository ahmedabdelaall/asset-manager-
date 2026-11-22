/* Service worker: makes the app installable and opens it even on a bad connection.
   Privacy: API answers (people, assets, national IDs...) are NEVER cached - only the app's own files. */
const CACHE = 'am-shell-v1';
const SHELL = ['/', '/static/app.css', '/static/app.js', '/static/qr.js', '/static/i18n/en.json', '/static/i18n/ar.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).catch(() => { }).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET' || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/brand/')) return;      // always live, never stored
  const isShell = url.pathname === '/' || url.pathname === '/index.html' || url.pathname.startsWith('/static/');
  if (!isShell) return;
  // network first (updates reach phones immediately), cached copy only when offline
  e.respondWith(fetch(req).then(res => {
    if (res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(url.pathname === '/index.html' ? '/' : req, copy)); }
    return res;
  }).catch(() => caches.match(url.pathname === '/index.html' ? '/' : req).then(r => r || new Response(
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><body style="font-family:sans-serif;padding:24px">' +
    '<h2>Offline · غير متصل</h2><p>Connect to the internet and try again.</p><p dir="rtl">اتصل بالإنترنت ثم حاول مرة أخرى.</p>',
    { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }))));
});

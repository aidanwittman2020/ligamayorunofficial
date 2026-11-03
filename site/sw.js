// Liga Mayor Unofficial: service worker.
// Pages: network first (always fresh), saved copy only when there is no connection.
// Google Sheet data: network first, last copy as backup offline.
// Images, icons and fonts: served from the saved copy, refreshed in background.
const V = 'lmu-v2';
const SHELL = ['/', '/historia/', '/manifest.webmanifest', '/icons/icon-192.png', '/icons/apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

// Key without the cache-busting "t" parameter, so the offline copy is found.
function keyOf(req) {
  const u = new URL(req.url);
  u.searchParams.delete('t');
  if (req.mode === 'navigate') u.search = '';
  return u.toString();
}
async function networkFirst(req) {
  const c = await caches.open(V);
  const key = keyOf(req);
  try {
    const r = await fetch(req);
    if (r && r.ok) c.put(key, r.clone());
    return r;
  } catch (err) {
    const hit = await c.match(key);
    if (hit) return hit;
    if (req.mode === 'navigate') return c.match('/');
    throw err;
  }
}
async function cacheFirst(req) {
  const c = await caches.open(V);
  const hit = await c.match(req);
  const net = fetch(req).then(r => { if (r && (r.ok || r.type === 'opaque')) c.put(req, r.clone()); return r; }).catch(() => hit);
  return hit || net;
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const u = new URL(req.url);
  if (/google-analytics\.com|googletagmanager\.com/.test(u.host)) return; // analytics: never cache
  if (req.mode === 'navigate') return e.respondWith(networkFirst(req));
  if (u.host === 'docs.google.com' || u.host.endsWith('googleusercontent.com')) return e.respondWith(networkFirst(req));
  if (u.origin === location.origin && /\.(png|webmanifest)$/.test(u.pathname)) return e.respondWith(cacheFirst(req));
  if (/fonts\.(googleapis|gstatic)\.com/.test(u.host)) return e.respondWith(cacheFirst(req));
});

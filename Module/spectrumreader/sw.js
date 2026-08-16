const CACHE = 'energy-graph-scan-module-v6.3.4';

const APP_SHELL = [
  './',
  './index.html',
  './styles.css?v=6.3.4',
  './core.js?v=6.3.4',
  './analysis_core_v2.js?v=6.3.4',
  './robust_core_v3.js?v=6.3.4',
  './canonical_registration_v4.js?v=6.3.4',
  './app.js?v=6.3.4',
  './manifest.webmanifest',
  './version.json',
  './analysis_contract_v2.json',
  './analysis_contract_v3.json',
  './analysis_contract_v4.json',
  './analysis_contract_v5.json',
  './icons/icon-180.png',
  './icons/icon-512.png'
];

const scopeURL = path => new URL(path, self.registration.scope).href;

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE)
      .then(cache => cache.addAll(APP_SHELL.map(scopeURL)))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(
        keys
          .filter(k => k.startsWith('energy-graph-scan-') && k !== CACHE)
          .map(k => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  const scope = new URL(self.registration.scope);
  const inScope = url.origin === scope.origin && url.pathname.startsWith(scope.pathname);

  // Never let this module service worker intercept another app outside
  // /Module/spectrumreader/, even on the same GitHub Pages origin.
  if (!inScope) return;

  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req, {cache:'no-store'})
        .then(res => {
          if (res.ok) {
            const copy=res.clone();
            caches.open(CACHE).then(c => c.put(scopeURL('./index.html'),copy));
          }
          return res;
        })
        .catch(() =>
          caches.match(scopeURL('./index.html'))
            .then(r => r || caches.match(scopeURL('./')))
        )
    );
    return;
  }

  // Network-first while online; exact module-local cache fallback offline.
  if (/\.(?:css|js|json|webmanifest)$/.test(url.pathname)) {
    event.respondWith(
      fetch(req,{cache:'no-store'})
        .then(res => {
          if (res.ok) {
            const copy=res.clone();
            caches.open(CACHE).then(c => c.put(req,copy));
          }
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  event.respondWith(
    caches.match(req)
      .then(cached => cached || fetch(req).then(res => {
        if (res.ok) {
          const copy=res.clone();
          caches.open(CACHE).then(c => c.put(req,copy));
        }
        return res;
      }))
  );
});

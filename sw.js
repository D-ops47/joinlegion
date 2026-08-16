/* LEGION service worker.
   Purpose is narrow and deliberate: Chrome will not treat a site as
   installable (and so will never fire beforeinstallprompt) unless a service
   worker with a fetch handler is registered. That prompt is what makes the
   "Save this" button able to put a real icon on an Android home screen.

   Caching strategy is intentionally conservative. The card is generated from
   the person's answers at runtime and the counter is live, so caching HTML
   would serve stale numbers and stale copy after a deploy. We therefore:
     - never cache HTML or /api/* — always straight to the network
     - cache-first only the immutable assets (icons and the agent clips)
   Everything else falls through to the network untouched. */

/* Bumped to v2 when the agent clips changed from mp4/webm to animated WebP.
   The activate handler deletes every cache whose name is not the current one,
   so bumping this is what evicts the old video files from returning visitors. */
const CACHE = 'legion-v2';

/* Static, content-stable files. Safe to serve from cache because they change
   only when their filename changes. */
const PRECACHE = [
  '/assets/icon-192.png',
  '/assets/icon-512.png',
  '/assets/icon-180.png'
];

self.addEventListener('install', (e) => {
  /* Take over immediately rather than waiting for every tab to close, so a
     fresh deploy is not shadowed by an old worker. */
  self.skipWaiting();
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE)).catch(() => {})
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;

  /* Only GETs are cacheable; /api/track is a POST and must never be touched. */
  if (req.method !== 'GET') return;

  const url = new URL(req.url);

  /* Same-origin only. Fonts and anything third-party go straight out. */
  if (url.origin !== self.location.origin) return;

  /* Live data and documents always come from the network so the counter and
     any copy changes are current the moment they deploy. */
  if (url.pathname.startsWith('/api/')) return;
  if (req.mode === 'navigate' || req.destination === 'document') return;

  /* Immutable media and icons: cache-first, then fill the cache on miss. */
  const cacheable = /^\/assets\//.test(url.pathname);
  if (!cacheable) return;

  e.respondWith(
    caches.match(req).then((hit) => {
      if (hit) return hit;
      return fetch(req).then((res) => {
        /* Only complete 200s are cacheable. Byte-range responses are 206 and
           must be passed through untouched. */
        if (res && res.status === 200 && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      }).catch(() => hit);
    })
  );
});

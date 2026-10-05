/* ---------------------------------------------------------------------------
 * KEMTA — service worker
 *
 * Objectifs, dans l'ordre :
 *   1. l'application installée doit s'ouvrir sans réseau (coquille en cache) ;
 *   2. les visuels (photos de chantier, icônes) doivent se réafficher hors ligne ;
 *   3. les appels API de suivi doivent rester frais : jamais de donnée de
 *      budget ou d'avancement servie depuis un cache périmé.
 *
 * Aucune donnée de projet n'est mise en cache : le service worker ne sert que
 * la coquille de l'application et les ressources statiques.
 * ------------------------------------------------------------------------- */
const VERSION = 'kemta-v1';
const SHELL_CACHE = `${VERSION}-shell`;
const ASSET_CACHE = `${VERSION}-assets`;

const SHELL_URLS = ['/', '/manifest.webmanifest', '/favicon.svg'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL_URLS))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting()),
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Même origine uniquement : le service worker n'intercepte pas les services
  // externes (SMS, paiement, tuiles de carte).
  if (url.origin !== self.location.origin) return;

  // API, documents et espaces connectés : toujours le réseau.
  if (
    url.pathname.startsWith('/api/') ||
    url.pathname.startsWith('/media/') ||
    url.pathname.startsWith('/espace') ||
    url.pathname.startsWith('/connexion')
  ) {
    return;
  }

  // Ressources statiques : cache d'abord pour les assets versionnés.
  if (url.pathname.startsWith('/images/') || url.pathname.startsWith('/icons/') || url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.open(ASSET_CACHE).then(async (cache) => {
        const cached = await cache.match(request);
        if (cached) return cached;
        try {
          const response = await fetch(request);
          if (response.ok) cache.put(request, response.clone());
          return response;
        } catch (error) {
          return cached || Response.error();
        }
      }),
    );
    return;
  }

  // Navigations : réseau d'abord (contenu à jour), repli sur la coquille en cache.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone();
          caches.open(SHELL_CACHE).then((cache) => cache.put('/', copy)).catch(() => {});
          return response;
        })
        .catch(() => caches.match('/').then((cached) => cached || Response.error())),
    );
    return;
  }

  // Reste : réseau, avec repli silencieux sur le cache si coupure.
  event.respondWith(
    fetch(request).catch(() => caches.match(request).then((cached) => cached || Response.error())),
  );
});

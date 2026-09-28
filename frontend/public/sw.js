/* LuluSchools — service worker (Lot 7.5, connectivité limitée).
 *
 * - Coquille de l'application (index.html, scripts et styles) : l'application s'ouvre
 *   même sans réseau, sur les écrans déjà visités.
 * - Contenus pédagogiques déjà consultés (cours, devoirs, bulletins, profil) :
 *   « réseau d'abord, copie locale sinon » — toujours la donnée fraîche quand le réseau
 *   répond, la dernière copie quand il ne répond pas.
 * - Rien d'autre n'est mis en cache côté API (paiements, messages, actions : jamais).
 * - La copie locale est effacée à la déconnexion (téléphone partagé) : message
 *   { type: "vider-donnees" } envoyé par l'application.
 */
const VERSION = "lulu-v1";
const CACHE_COQUILLE = `${VERSION}-coquille`;
const CACHE_API = `${VERSION}-contenus`;

const COQUILLE = ["/", "/manifest.webmanifest", "/preferences-initiales.js", "/logo.webp", "/favicon.svg"];

// GET d'API lisibles hors ligne. Les liens signés vers des fichiers (qui expirent) sont exclus.
const API_HORS_LIGNE = [
  /^\/api\/v1\/me$/,
  /^\/api\/v1\/me\/compteurs$/,
  /^\/api\/v1\/eleves\/me(\/passeport)?$/,
  /^\/api\/v1\/tuteurs\/me\/inscriptions$/,
  /^\/api\/v1\/classes\/[^/]+\/(cours|devoirs|periodes)$/,
  /^\/api\/v1\/cours\/[^/]+(\/quiz)?$/,
  /^\/api\/v1\/quiz\/[^/]+$/,
  /^\/api\/v1\/devoirs\/[^/]+(\/ma-soumission)?$/,
  /^\/api\/v1\/eleves\/[^/]+\/bulletins(\/detail)?$/,
  /^\/api\/v1\/ecoute\/.+$/,
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_COQUILLE).then((cache) => cache.addAll(COQUILLE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((cles) => Promise.all(cles.filter((c) => !c.startsWith(VERSION)).map((c) => caches.delete(c))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("message", (event) => {
  if (event.data && event.data.type === "vider-donnees") event.waitUntil(caches.delete(CACHE_API));
});

async function reseauDabord(requete, nomCache) {
  const cache = await caches.open(nomCache);
  try {
    const reponse = await fetch(requete);
    if (reponse.ok) cache.put(requete, reponse.clone());
    return reponse;
  } catch (erreur) {
    // ignoreVary : la copie reste lisible après un rafraîchissement du jeton d'accès.
    const copie = await cache.match(requete, { ignoreVary: true });
    if (copie) return copie;
    throw erreur;
  }
}

async function cacheDabord(requete) {
  const cache = await caches.open(CACHE_COQUILLE);
  const copie = await cache.match(requete);
  if (copie) return copie;
  const reponse = await fetch(requete);
  if (reponse.ok) cache.put(requete, reponse.clone());
  return reponse;
}

self.addEventListener("fetch", (event) => {
  const requete = event.request;
  if (requete.method !== "GET") return;
  const url = new URL(requete.url);
  if (url.origin !== self.location.origin) return;

  // Navigation (SPA) : la page à jour si possible, sinon la coquille en cache.
  if (requete.mode === "navigate") {
    event.respondWith(
      fetch(requete)
        .then((reponse) => {
          const copie = reponse.clone();
          caches.open(CACHE_COQUILLE).then((cache) => cache.put("/", copie));
          return reponse;
        })
        .catch(() => caches.match("/")),
    );
    return;
  }

  // Scripts et styles versionnés par Vite (nom haché) : immuables, cache d'abord.
  if (url.pathname.startsWith("/assets/")) {
    event.respondWith(cacheDabord(requete));
    return;
  }

  if (url.pathname.startsWith("/api/")) {
    if (API_HORS_LIGNE.some((motif) => motif.test(url.pathname))) event.respondWith(reseauDabord(requete, CACHE_API));
    return;
  }

  // Icônes, polices locales, sons du mode Écoute : cache d'abord.
  if (/\.(png|webp|svg|ico|woff2?|mp3|ogg|json|webmanifest)$/.test(url.pathname)) {
    event.respondWith(cacheDabord(requete));
  }
});

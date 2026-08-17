// Bump VERSION to force clients onto a fresh cache after a deploy.
const VERSION = 'v2';
const CACHE = `tracker-${VERSION}`;

// Relative URLs so the app works both at a domain root and under a
// GitHub Pages project path such as /Tracker/.
const CORE = [
  './',
  './index.html',
  './manifest.json',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

// Cached so the app still boots offline; without it the Supabase client is
// simply absent and the app falls back to local-only mode.
const VENDOR = ['https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2'];

self.addEventListener('install', (event)=>{
  event.waitUntil((async ()=>{
    const cache = await caches.open(CACHE);
    // Added one by one: a single unreachable URL must not fail the install.
    await Promise.all([...CORE, ...VENDOR].map(url=>
      cache.add(new Request(url, { cache: 'reload' })).catch(()=>{})
    ));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event)=>{
  event.waitUntil((async ()=>{
    const names = await caches.keys();
    await Promise.all(names.filter(n=>n !== CACHE).map(n=>caches.delete(n)));
    await self.clients.claim();
  })());
});

async function networkFirst(request){
  const cache = await caches.open(CACHE);
  try{
    const fresh = await fetch(request);
    if(fresh && fresh.ok) cache.put(request, fresh.clone());
    return fresh;
  }catch(err){
    const cached = await cache.match(request) || await cache.match('./index.html');
    if(cached) return cached;
    throw err;
  }
}

async function cacheFirst(request){
  const cache = await caches.open(CACHE);
  const cached = await cache.match(request);
  if(cached) return cached;
  const fresh = await fetch(request);
  if(fresh && fresh.ok) cache.put(request, fresh.clone());
  return fresh;
}

self.addEventListener('fetch', (event)=>{
  const request = event.request;
  if(request.method !== 'GET') return;

  const url = new URL(request.url);
  const sameOrigin = url.origin === self.location.origin;

  // Supabase auth and REST traffic must never be served from cache.
  if(!sameOrigin){
    if(VENDOR.some(v=>request.url.startsWith(v))) event.respondWith(cacheFirst(request));
    return;
  }

  // The document is network-first so a new deploy is picked up immediately.
  if(request.mode === 'navigate' || url.pathname.endsWith('/index.html')){
    event.respondWith(networkFirst(request));
    return;
  }

  event.respondWith(cacheFirst(request));
});

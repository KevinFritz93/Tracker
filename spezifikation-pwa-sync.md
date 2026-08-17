# Auftrag: Aktivitäten-Tracker zu PWA mit Cloud-Sync ausbauen

Repo: https://github.com/KevinFritz93/Tracker
Basisdatei: `aktivitaeten-tracker.html`

## Ziel
Die bestehende Single-File-HTML-App soll:
1. als installierbare PWA auf dem Smartphone laufen (offline-fähig),
2. Aktivitäten über Supabase synchronisieren (statt nur `localStorage`),
3. Login per Google (Supabase Auth),
4. weiterhin einfach erweiterbar bleiben (kein Build-Tooling nötig).

## Supabase-Zugangsdaten
```
SUPABASE_URL=https://hfzuoeglrttdgtdjdrwe.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_MW082YZbu_tiY4ypwO76jQ_ipHp5fom
```
**Wichtig:** Nur der `PUBLISHABLE_KEY` darf im Frontend-Code landen. Der `SECRET_KEY` wird für dieses Projekt nicht gebraucht und darf niemals im Repo oder im Client-Code auftauchen.

Google-Login ist in Supabase (Authentication → Providers → Google) bereits aktiviert.

## 1. Datenbank-Schema (in Supabase SQL-Editor ausführen)

```sql
create table public.activities (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null default auth.uid(),
  date date not null,
  time time,
  text text not null,
  description text,
  mood integer not null check (mood >= 0 and mood <= 10),
  reason text,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

alter table public.activities enable row level security;

create policy "Nutzer sehen nur eigene Einträge"
  on public.activities for select
  using (auth.uid() = user_id);

create policy "Nutzer erstellen eigene Einträge"
  on public.activities for insert
  with check (auth.uid() = user_id);

create policy "Nutzer bearbeiten eigene Einträge"
  on public.activities for update
  using (auth.uid() = user_id);

create policy "Nutzer löschen eigene Einträge"
  on public.activities for delete
  using (auth.uid() = user_id);
```

Row Level Security stellt sicher, dass jeder Nutzer (auch bei mehreren Google-Konten) nur seine eigenen Daten sieht.

## 2. Dateistruktur im Repo

```
/index.html              (umbenannt von aktivitaeten-tracker.html)
/manifest.json
/service-worker.js
/icons/icon-192.png
/icons/icon-512.png
```

## 3. manifest.json

```json
{
  "name": "Aktivitäten-Tracker",
  "short_name": "Tracker",
  "start_url": "/index.html",
  "display": "standalone",
  "background_color": "#faf7f0",
  "theme_color": "#faf7f0",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```
Im `<head>` von `index.html` ergänzen:
```html
<link rel="manifest" href="/manifest.json">
<meta name="theme-color" content="#faf7f0">
```

## 4. service-worker.js (Grundgerüst)

```javascript
const CACHE_NAME = 'tracker-v1';
const ASSETS = ['/index.html', '/manifest.json'];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)));
});

self.addEventListener('fetch', (e) => {
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
```
Registrierung am Ende von `index.html`:
```html
<script>
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/service-worker.js');
  }
</script>
```

## 5. Supabase-Client & Auth (in index.html einbinden)

```html
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
<script>
  const supabase = window.supabase.createClient(
    'https://hfzuoeglrttdgtdjdrwe.supabase.co',
    'sb_publishable_MW082YZbu_tiY4ypwO76jQ_ipHp5fom'
  );

  async function signIn() {
    await supabase.auth.signInWithOAuth({ provider: 'google' });
  }

  async function signOut() {
    await supabase.auth.signOut();
  }
</script>
```

## 6. Sync-Logik (Kernidee)

Bestehende `loadEntries()` / `saveEntries()`-Funktionen umbauen zu Offline-First:

- **Lesen:** zuerst aus `localStorage` anzeigen (sofortige Ladezeit, offline nutzbar), danach im Hintergrund `supabase.from('activities').select()` aufrufen und die Anzeige aktualisieren.
- **Schreiben:** Eintrag sofort in `localStorage` speichern (UI reagiert sofort), danach `supabase.from('activities').insert(...)` bzw. `.update(...)` aufrufen. Bei fehlender Verbindung: Eintrag in einer lokalen „Warteschlange" merken und beim nächsten Onlinegang nachsynchronisieren (z. B. über das `online`-Event im Browser).
- **Konfliktregel:** „Last write wins" über `updated_at` reicht für einen Einzelnutzer-Tracker völlig aus — keine komplexe Konfliktlösung nötig.

## 7. Deployment

- GitHub Pages im Repo aktivieren (Settings → Pages → Branch `main`, Root).
- HTTPS ist bei GitHub Pages automatisch gegeben (Voraussetzung für Service Worker).
- Nach dem ersten Deploy: Seite auf dem Smartphone öffnen → „Zum Startbildschirm hinzufügen".

## Offene Punkte für den Agenten
- Icons (192x192, 512x512 PNG) müssen noch erstellt werden — einfaches Platzhalter-Icon reicht zum Start.
- Login-Button und Logout-Button im UI ergänzen (z. B. oben in der Kopfzeile).
- Beim ersten Laden ohne Login: entweder Login erzwingen oder App im reinen Lokalmodus weiter nutzbar lassen (Entscheidung liegt beim Nutzer).

# Aktivitäten-Tracker

Ein Tagebuch für Aktivitäten, Stimmung und Tagesgefühl – nach dem Prinzip der
Verhaltensaktivierung. Die App läuft als installierbare PWA, funktioniert
offline und synchronisiert optional über Supabase zwischen mehreren Geräten.

Kein Build-Tooling: die App besteht aus statischen Dateien und lässt sich
direkt über GitHub Pages ausliefern.

## Dateien

| Datei                 | Zweck                                                  |
| --------------------- | ------------------------------------------------------ |
| `index.html`          | die komplette App (Markup, Styles, Logik)               |
| `manifest.json`       | PWA-Manifest (Name, Icons, Startseite)                  |
| `service-worker.js`   | Offline-Cache                                           |
| `icons/`              | App-Icons in 192 px und 512 px                          |
| `supabase-schema.sql` | Tabellen und Row Level Security für Supabase            |

## Einrichtung

### 1. Datenbank anlegen

`supabase-schema.sql` im Supabase SQL-Editor ausführen. Das Skript ist
wiederholbar und ergänzt fehlende Spalten, falls schon eine ältere Version der
Tabelle `activities` existiert.

Es werden zwei Tabellen angelegt:

- `activities` – eine Zeile pro Aktivität
- `day_reviews` – eine Zeile pro Tag für das Tagesgefühl

Row Level Security sorgt dafür, dass jedes Konto ausschließlich die eigenen
Zeilen sieht.

### 2. Google-Login konfigurieren

Google ist unter *Authentication → Providers* bereits aktiviert. Zusätzlich
muss die Adresse der veröffentlichten App unter
*Authentication → URL Configuration* hinterlegt werden, sonst bricht der Login
nach der Google-Weiterleitung ab:

- **Site URL:** `https://kevinfritz93.github.io/Tracker/`
- **Redirect URLs:** `https://kevinfritz93.github.io/Tracker/` zusätzlich
  eintragen (bei lokalen Tests auch `http://localhost:8000/`)

### 3. Veröffentlichen

*Settings → Pages → Branch `main`, Ordner `/ (root)`.* GitHub Pages liefert
automatisch über HTTPS aus, was Voraussetzung für Service Worker und Login ist.

Danach die Seite auf dem Smartphone öffnen und „Zum Startbildschirm
hinzufügen" wählen.

### Lokal testen

Ein Service Worker läuft nicht über `file://`. Für lokale Tests genügt:

```bash
python3 -m http.server 8000
```

Dann `http://localhost:8000/` öffnen.

Im Ordner `_test/` liegen automatische Tests, die die App in einem echten
Browser (headless Chromium) starten und den Abgleich sowie den Service Worker
prüfen:

```bash
./_test/run.sh
```

Der Ordner gehört nicht zur App und kann gelöscht werden.

## Wie die Synchronisierung funktioniert

Die App ist **offline-first**: `localStorage` ist immer die Quelle für die
Anzeige, die Cloud ist eine Kopie davon. Dadurch startet die App sofort und
bleibt ohne Netz vollständig bedienbar.

- **Ohne Login** funktioniert alles wie vorher, die Daten bleiben auf dem Gerät.
- **Nach dem Login** werden lokale Daten hochgeladen und mit dem Server
  abgeglichen. Vorhandene Einträge gehen dabei nicht verloren – sie werden beim
  ersten Abgleich in die Cloud übernommen.

Jeder Datensatz trägt drei zusätzliche Felder:

- `updated_at` – entscheidet bei Konflikten, welche Version gewinnt
  („last write wins")
- `deleted_at` – markiert Gelöschtes, statt es sofort zu entfernen. Nur so
  erfährt ein zweites Gerät überhaupt von der Löschung.
- `dirty` – lokal geändert und noch nicht übertragen. Das Flag liegt im
  `localStorage` und übersteht deshalb einen Neustart: Änderungen im Flugmodus
  gehen nicht verloren.

Abgeglichen wird beim Laden, nach jeder Änderung (kurz verzögert), beim
Zurückkehren auf den Tab und sobald das Gerät wieder online geht. Die Leiste
oben zeigt jederzeit den Stand an.

## Sicherheit

Im Frontend steht ausschließlich der **Publishable Key**. Dieser ist für den
Client gedacht und darf öffentlich sein; der Zugriffsschutz liegt bei Row Level
Security in der Datenbank. Der Secret Key wird nicht benötigt und gehört
niemals in dieses Repository.

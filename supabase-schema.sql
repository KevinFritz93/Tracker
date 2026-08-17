-- Aktivitäten-Tracker – Schema für Supabase
--
-- Im Supabase SQL-Editor ausführen. Das Skript ist wiederholbar: es kann auch
-- dann laufen, wenn die Tabelle "activities" schon aus einer früheren Version
-- existiert – fehlende Spalten und Policies werden dann nur ergänzt.
--
-- Unterschiede zur ersten Fassung aus der Spezifikation:
--   * "deleted_at" als Soft-Delete. Ohne diese Spalte kann ein Gerät nicht
--     erfahren, dass ein Eintrag auf einem anderen Gerät gelöscht wurde – der
--     Eintrag käme beim nächsten Abgleich einfach zurück.
--   * Tabelle "day_reviews" für das Tagesgefühl (ein Eintrag pro Tag).
--   * "updated_at" wird bewusst vom Client gesetzt, weil der Abgleich darüber
--     entscheidet, welche Version gewinnt ("last write wins"). Deshalb gibt es
--     hier absichtlich keinen Trigger, der die Spalte überschreibt.

-- ---------------------------------------------------------------- activities
create table if not exists public.activities (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null default auth.uid(),
  date date not null,
  time time,
  text text not null,
  description text,
  mood integer not null check (mood >= 0 and mood <= 10),
  reason text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  deleted_at timestamptz
);

alter table public.activities add column if not exists deleted_at timestamptz;
alter table public.activities add column if not exists updated_at timestamptz default now();

create index if not exists activities_user_date_idx
  on public.activities (user_id, date);

alter table public.activities enable row level security;

drop policy if exists "Nutzer sehen nur eigene Einträge" on public.activities;
create policy "Nutzer sehen nur eigene Einträge"
  on public.activities for select
  using (auth.uid() = user_id);

drop policy if exists "Nutzer erstellen eigene Einträge" on public.activities;
create policy "Nutzer erstellen eigene Einträge"
  on public.activities for insert
  with check (auth.uid() = user_id);

drop policy if exists "Nutzer bearbeiten eigene Einträge" on public.activities;
create policy "Nutzer bearbeiten eigene Einträge"
  on public.activities for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Nutzer löschen eigene Einträge" on public.activities;
create policy "Nutzer löschen eigene Einträge"
  on public.activities for delete
  using (auth.uid() = user_id);

-- --------------------------------------------------------------- day_reviews
-- Genau ein Tagesgefühl pro Nutzer und Datum.
create table if not exists public.day_reviews (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users not null default auth.uid(),
  date date not null,
  mood integer not null check (mood >= 0 and mood <= 10),
  note text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  deleted_at timestamptz,
  unique (user_id, date)
);

create index if not exists day_reviews_user_date_idx
  on public.day_reviews (user_id, date);

alter table public.day_reviews enable row level security;

drop policy if exists "Nutzer sehen nur eigene Tage" on public.day_reviews;
create policy "Nutzer sehen nur eigene Tage"
  on public.day_reviews for select
  using (auth.uid() = user_id);

drop policy if exists "Nutzer erstellen eigene Tage" on public.day_reviews;
create policy "Nutzer erstellen eigene Tage"
  on public.day_reviews for insert
  with check (auth.uid() = user_id);

drop policy if exists "Nutzer bearbeiten eigene Tage" on public.day_reviews;
create policy "Nutzer bearbeiten eigene Tage"
  on public.day_reviews for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Nutzer löschen eigene Tage" on public.day_reviews;
create policy "Nutzer löschen eigene Tage"
  on public.day_reviews for delete
  using (auth.uid() = user_id);

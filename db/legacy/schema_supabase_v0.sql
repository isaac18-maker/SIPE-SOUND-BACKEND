-- =========================================================
-- HISTORICO. NO EJECUTAR. Ver migrations/ (HU-B-303).
-- Copia del script del antiguo monorepo (SIPE-SOUND-FULLSTACK/database/schema.sql).
-- Esta DESACTUALIZADO respecto a la base real: ver db/legacy/INVENTARIO.md.
-- =========================================================

-- =========================================================
--  GuitarApp — Base de datos FINAL (versión combinada)
--  Pega esto en: Supabase → SQL Editor → Run
-- =========================================================
-- Combina: estructura simple (arrays, campo "nivel" directo)
-- + tabla de partituras + seguridad correcta con auth.users de Supabase

-- ---------------------------------------------------------
-- 1. PROFILES (perfil del usuario)
-- NO guardamos password aquí: Supabase Auth (auth.users) ya
-- maneja login, hash de contraseña, recuperación, etc.
-- ---------------------------------------------------------
create table profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  nombre      text not null,
  nivel       text not null default 'principiante'
                    check (nivel in ('principiante','intermedio','avanzado')),
  creado_en   timestamp with time zone default now()
);

-- Crea el perfil automáticamente cuando alguien se registra
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, nombre, nivel)
  values (new.id, coalesce(new.raw_user_meta_data->>'nombre', new.email), 'principiante');
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

-- ---------------------------------------------------------
-- 2. LECCIONES
-- ---------------------------------------------------------
create table lecciones (
  id          serial primary key,
  numero      int not null,
  titulo      text not null,
  descripcion text,
  nivel       text not null default 'principiante'
                    check (nivel in ('principiante','intermedio','avanzado')),
  duracion    text,
  acordes     text[],
  temas       text[],
  creado_en   timestamp with time zone default now()
);

-- ---------------------------------------------------------
-- 3. EJERCICIOS
-- ---------------------------------------------------------
create table ejercicios (
  id              serial primary key,
  leccion_id      int references lecciones(id) on delete set null,
  nombre          text not null,
  descripcion     text,
  nivel           text not null default 'principiante'
                        check (nivel in ('principiante','intermedio','avanzado')),
  bpm_recomendado int default 60,
  duracion        text,
  compas          text default '4/4',
  acordes         text[],
  pasos           text[],
  creado_en       timestamp with time zone default now()
);

-- ---------------------------------------------------------
-- 4. ACORDES
-- ---------------------------------------------------------
create table acordes (
  id          serial primary key,
  nombre      text not null unique,
  tipo        text check (tipo in ('mayor','menor','septima','disminuido')),
  descripcion text,
  dificultad  text default 'facil'
                    check (dificultad in ('facil','medio','dificil')),
  creado_en   timestamp with time zone default now()
);

-- ---------------------------------------------------------
-- 5. PARTITURAS
-- ---------------------------------------------------------
create table partituras (
  id          serial primary key,
  titulo      text not null,
  artista     text,
  nivel       text default 'principiante'
                    check (nivel in ('principiante','intermedio','avanzado')),
  tipo        text check (tipo in ('partitura','tablatura','ambas')),
  acordes     text[],
  imagen_url  text,
  creado_en   timestamp with time zone default now()
);

-- ---------------------------------------------------------
-- 6. PROGRESO (genérico: sirve para lecciones y ejercicios)
-- ---------------------------------------------------------
create table progreso (
  id             uuid primary key default gen_random_uuid(),
  usuario_id     uuid not null references auth.users(id) on delete cascade,
  tipo           text not null check (tipo in ('leccion','ejercicio')),
  contenido_id   int not null,
  porcentaje     int not null default 0 check (porcentaje between 0 and 100),
  completado     boolean default false,
  actualizado_en timestamp with time zone default now(),
  unique (usuario_id, tipo, contenido_id)
);

-- =========================================================
-- ROW LEVEL SECURITY (RLS)
-- =========================================================
alter table profiles   enable row level security;
alter table lecciones  enable row level security;
alter table ejercicios enable row level security;
alter table acordes    enable row level security;
alter table partituras enable row level security;
alter table progreso   enable row level security;

-- Contenido del curso: cualquiera puede leer (no requiere login)
create policy "Lectura pública lecciones"  on lecciones  for select using (true);
create policy "Lectura pública ejercicios" on ejercicios for select using (true);
create policy "Lectura pública acordes"    on acordes    for select using (true);
create policy "Lectura pública partituras" on partituras for select using (true);

-- Perfil: cada quien ve y edita solo el suyo
create policy "Ver propio perfil"    on profiles for select using (auth.uid() = id);
create policy "Editar propio perfil" on profiles for update using (auth.uid() = id);

-- Progreso: cada quien ve y edita solo el suyo
create policy "Ver propio progreso"        on progreso for select using (auth.uid() = usuario_id);
create policy "Insertar propio progreso"   on progreso for insert with check (auth.uid() = usuario_id);
create policy "Actualizar propio progreso" on progreso for update using (auth.uid() = usuario_id);

-- =========================================================
-- DATOS DE PRUEBA (opcional, para probar el frontend ya mismo)
-- =========================================================
insert into acordes (nombre, tipo, dificultad) values
  ('Em', 'menor', 'facil'),
  ('Am', 'menor', 'facil'),
  ('C',  'mayor', 'facil'),
  ('G',  'mayor', 'medio'),
  ('D',  'mayor', 'medio');

insert into lecciones (numero, titulo, descripcion, nivel, duracion, acordes, temas) values
  (1, 'Postura y primeros acordes', 'Aprende a sostener la guitarra y tu primer acorde', 'principiante', '30 min', array['Em'], array['Postura','Afinación']),
  (2, 'Cambio entre Em y Am', 'Practica cambiar de acorde de forma fluida', 'principiante', '25 min', array['Em','Am'], array['Cambios de acorde']),
  (3, 'Acordes mayores C y G', 'Suma dos acordes mayores a tu repertorio', 'principiante', '35 min', array['C','G'], array['Acordes mayores']);

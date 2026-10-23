-- =========================================================
-- Inventario REAL del esquema public (solo lectura, generado).
-- REFERENCIA. NO EJECUTAR. Generado por scripts/inventariar_esquema.py
-- =========================================================
-- PostgreSQL 17.6

-- ---------------------------------------------------------
-- public.acordes
create table public.acordes (
  id integer not null default nextval('acordes_id_seq'::regclass),
  nombre text not null,
  tipo text,
  descripcion text,
  dificultad text default 'facil'::text,
  creado_en timestamp with time zone default now(),
  diagram jsonb,
  constraint acordes_nombre_key UNIQUE (nombre),
  constraint acordes_pkey PRIMARY KEY (id),
  constraint acordes_dificultad_check CHECK ((dificultad = ANY (ARRAY['facil'::text, 'medio'::text, 'dificil'::text]))),
  constraint acordes_tipo_check CHECK ((tipo = ANY (ARRAY['mayor'::text, 'menor'::text, 'septima'::text, 'disminuido'::text])))
);
alter table public.acordes enable row level security;
-- politica "Lectura pública acordes": SELECT para {public} (PERMISSIVE) using (true)
-- privilegios de anon: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
-- privilegios de authenticated: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE

-- ---------------------------------------------------------
-- public.bloques
create table public.bloques (
  id integer not null default nextval('bloques_id_seq'::regclass),
  numero integer not null,
  titulo text not null,
  descripcion text,
  nivel text not null default 'principiante'::text,
  orden_index integer not null,
  creado_en timestamp with time zone default now(),
  constraint bloques_pkey PRIMARY KEY (id),
  constraint bloques_nivel_check CHECK ((nivel = ANY (ARRAY['principiante'::text, 'intermedio'::text, 'avanzado'::text])))
);
alter table public.bloques enable row level security;
-- politica "Lectura publica bloques": SELECT para {public} (PERMISSIVE) using (true)
-- privilegios de anon: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
-- privilegios de authenticated: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE

-- ---------------------------------------------------------
-- public.ejercicios
create table public.ejercicios (
  id integer not null default nextval('ejercicios_id_seq'::regclass),
  leccion_id integer,
  nombre text not null,
  descripcion text,
  nivel text not null default 'principiante'::text,
  bpm_recomendado integer default 60,
  duracion text,
  compas text default '4/4'::text,
  acordes text[],
  pasos text[],
  creado_en timestamp with time zone default now(),
  constraint ejercicios_pkey PRIMARY KEY (id),
  constraint ejercicios_leccion_id_fkey FOREIGN KEY (leccion_id) REFERENCES lecciones(id) ON DELETE SET NULL,
  constraint ejercicios_nivel_check CHECK ((nivel = ANY (ARRAY['principiante'::text, 'intermedio'::text, 'avanzado'::text])))
);
alter table public.ejercicios enable row level security;
-- politica "Lectura pública ejercicios": SELECT para {public} (PERMISSIVE) using (true)
-- privilegios de anon: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
-- privilegios de authenticated: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE

-- ---------------------------------------------------------
-- public.lecciones
create table public.lecciones (
  id integer not null default nextval('lecciones_id_seq'::regclass),
  numero integer not null,
  titulo text not null,
  descripcion text,
  nivel text not null default 'principiante'::text,
  duracion text,
  acordes text[],
  temas text[],
  creado_en timestamp with time zone default now(),
  contenido text,
  bloque_id integer,
  constraint lecciones_pkey PRIMARY KEY (id),
  constraint lecciones_bloque_id_fkey FOREIGN KEY (bloque_id) REFERENCES bloques(id) ON DELETE SET NULL,
  constraint lecciones_nivel_check CHECK ((nivel = ANY (ARRAY['principiante'::text, 'intermedio'::text, 'avanzado'::text])))
);
alter table public.lecciones enable row level security;
-- politica "Lectura pública lecciones": SELECT para {public} (PERMISSIVE) using (true)
-- privilegios de anon: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
-- privilegios de authenticated: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE

-- ---------------------------------------------------------
-- public.partituras
create table public.partituras (
  id integer not null default nextval('partituras_id_seq'::regclass),
  titulo text not null,
  artista text,
  nivel text default 'principiante'::text,
  tipo text,
  acordes text[],
  imagen_url text,
  creado_en timestamp with time zone default now(),
  constraint partituras_pkey PRIMARY KEY (id),
  constraint partituras_nivel_check CHECK ((nivel = ANY (ARRAY['principiante'::text, 'intermedio'::text, 'avanzado'::text]))),
  constraint partituras_tipo_check CHECK ((tipo = ANY (ARRAY['partitura'::text, 'tablatura'::text, 'ambas'::text])))
);
alter table public.partituras enable row level security;
-- politica "Lectura pública partituras": SELECT para {public} (PERMISSIVE) using (true)
-- privilegios de anon: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
-- privilegios de authenticated: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE

-- ---------------------------------------------------------
-- public.profiles
create table public.profiles (
  id uuid not null,
  nombre text not null,
  nivel text not null default 'principiante'::text,
  creado_en timestamp with time zone default now(),
  constraint profiles_pkey PRIMARY KEY (id),
  constraint profiles_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE,
  constraint profiles_nivel_check CHECK ((nivel = ANY (ARRAY['principiante'::text, 'intermedio'::text, 'avanzado'::text])))
);
alter table public.profiles enable row level security;
-- politica "Editar propio perfil": UPDATE para {public} (PERMISSIVE) using ((auth.uid() = id))
-- politica "Ver propio perfil": SELECT para {public} (PERMISSIVE) using ((auth.uid() = id))
-- privilegios de anon: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
-- privilegios de authenticated: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE

-- ---------------------------------------------------------
-- public.progreso
create table public.progreso (
  id uuid not null default gen_random_uuid(),
  usuario_id uuid not null,
  tipo text not null,
  contenido_id integer not null,
  porcentaje integer not null default 0,
  completado boolean default false,
  actualizado_en timestamp with time zone default now(),
  constraint progreso_usuario_id_tipo_contenido_id_key UNIQUE (usuario_id, tipo, contenido_id),
  constraint progreso_pkey PRIMARY KEY (id),
  constraint progreso_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES auth.users(id) ON DELETE CASCADE,
  constraint progreso_porcentaje_check CHECK (((porcentaje >= 0) AND (porcentaje <= 100))),
  constraint progreso_tipo_check CHECK ((tipo = ANY (ARRAY['leccion'::text, 'ejercicio'::text, 'bloque'::text])))
);
alter table public.progreso enable row level security;
-- politica "Actualizar propio progreso": UPDATE para {public} (PERMISSIVE) using ((auth.uid() = usuario_id))
-- politica "Insertar propio progreso": INSERT para {public} (PERMISSIVE) with check ((auth.uid() = usuario_id))
-- politica "Ver propio progreso": SELECT para {public} (PERMISSIVE) using ((auth.uid() = usuario_id))
-- privilegios de anon: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
-- privilegios de authenticated: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE

-- ---------------------------------------------------------
-- public.quiz_preguntas
create table public.quiz_preguntas (
  id integer not null default nextval('quiz_preguntas_id_seq'::regclass),
  bloque_id integer not null,
  pregunta text not null,
  opciones text[] not null,
  respuesta_correcta integer not null,
  orden_index integer not null,
  creado_en timestamp with time zone default now(),
  constraint quiz_preguntas_pkey PRIMARY KEY (id),
  constraint quiz_preguntas_bloque_id_fkey FOREIGN KEY (bloque_id) REFERENCES bloques(id) ON DELETE CASCADE
);
alter table public.quiz_preguntas enable row level security;
-- politica "Lectura publica quiz_preguntas": SELECT para {public} (PERMISSIVE) using (true)
-- privilegios de anon: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE
-- privilegios de authenticated: DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE

-- ---------------------------------------------------------
-- Funciones de public
CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
begin
  insert into public.profiles (id, nombre, nivel)
  values (new.id, coalesce(new.raw_user_meta_data->>'nombre', new.email), 'principiante');
  return new;
end;
$function$
;
CREATE OR REPLACE FUNCTION public.rls_auto_enable()
 RETURNS event_trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$function$
;
-- ---------------------------------------------------------
-- Triggers (public y auth.users)
CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION handle_new_user();
-- ---------------------------------------------------------
-- Event triggers (base de datos completa)
-- ensure_rls: on ddl_command_end -> rls_auto_enable (estado O; tags: CREATE TABLE, CREATE TABLE AS, SELECT INTO)
-- issue_graphql_placeholder: on sql_drop -> set_graphql_placeholder (estado O; tags: DROP EXTENSION)
-- issue_pg_cron_access: on ddl_command_end -> grant_pg_cron_access (estado O; tags: CREATE EXTENSION)
-- issue_pg_graphql_access: on ddl_command_end -> grant_pg_graphql_access (estado O; tags: CREATE EXTENSION)
-- issue_pg_net_access: on ddl_command_end -> grant_pg_net_access (estado O; tags: CREATE EXTENSION)
-- pgrst_ddl_watch: on ddl_command_end -> pgrst_ddl_watch (estado O; tags: -)
-- pgrst_drop_watch: on sql_drop -> pgrst_drop_watch (estado O; tags: -)

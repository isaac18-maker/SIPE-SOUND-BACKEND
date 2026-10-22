"""Inventario de SOLO LECTURA del esquema `public` de la base de datos (HU-B-206).

Alternativa a `pg_dump --schema-only` cuando no esta instalado: lee el catalogo de
PostgreSQL y escribe la definicion exacta de cada objeto (las restricciones, indices,
funciones y triggers salen de pg_get_*def, es decir, el mismo SQL que usaria pg_dump).

Uso (DATABASE_URL del .env: Session pooler o conexion directa):

    uv run --with "psycopg[binary]" python scripts/inventariar_esquema.py

Salida: db/legacy/schema_real_<AAAAMMDD>.sql (DDL de referencia, NO se ejecuta).
La sesion se abre en modo solo lectura: el script no puede modificar nada.
"""

import os
import sys
from datetime import date
from pathlib import Path

import psycopg
from dotenv import dotenv_values

SALIDA = Path("db/legacy")

CONSULTA_TABLAS = """
select c.relname, c.relrowsecurity
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relkind = 'r'
order by c.relname
"""

CONSULTA_COLUMNAS = """
select a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,
       pg_get_expr(d.adbin, d.adrelid)
from pg_attribute a
left join pg_attrdef d on d.adrelid = a.attrelid and d.adnum = a.attnum
where a.attrelid = %s::regclass and a.attnum > 0 and not a.attisdropped
order by a.attnum
"""

CONSULTA_RESTRICCIONES = """
select conname, pg_get_constraintdef(oid)
from pg_constraint
where conrelid = %s::regclass
order by contype desc, conname
"""

CONSULTA_INDICES = """
select indexname, indexdef from pg_indexes
where schemaname = 'public' and tablename = %s
  and indexname not in (select conname from pg_constraint where conrelid = %s::regclass)
order by indexname
"""

CONSULTA_POLITICAS = """
select policyname, cmd, roles::text, permissive, qual, with_check
from pg_policies where schemaname = 'public' and tablename = %s
order by policyname
"""

CONSULTA_PRIVILEGIOS = """
select grantee, string_agg(privilege_type, ', ' order by privilege_type)
from information_schema.role_table_grants
where table_schema = 'public' and table_name = %s and grantee in ('anon', 'authenticated')
group by grantee order by grantee
"""

CONSULTA_FUNCIONES = """
select pg_get_functiondef(p.oid)
from pg_proc p join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public' and p.prokind = 'f'
order by p.proname
"""

# Triggers sobre tablas de public y sobre auth.users (handle_new_user vive alli).
CONSULTA_TRIGGERS = """
select pg_get_triggerdef(t.oid)
from pg_trigger t
join pg_class c on c.oid = t.tgrelid
join pg_namespace n on n.oid = c.relnamespace
where not t.tgisinternal
  and (n.nspname = 'public' or (n.nspname = 'auth' and c.relname = 'users'))
order by c.relname, t.tgname
"""

# Los event triggers (p. ej. rls_auto_enable de Supabase) no aparecen en pg_trigger.
CONSULTA_EVENT_TRIGGERS = """
select evtname, evtevent, evtfoid::regproc::text, evtenabled, array_to_string(evttags, ', ')
from pg_event_trigger
order by evtname
"""


def url_conexion() -> str:
    url = os.environ.get("DATABASE_URL") or dotenv_values(".env").get("DATABASE_URL")
    if not url:
        sys.exit("Falta DATABASE_URL (Session pooler de Supabase).")
    return url


def describir_tabla(cur: psycopg.Cursor, tabla: str, con_rls: bool) -> list[str]:
    nombre = f"public.{tabla}"
    lineas = ["-- ---------------------------------------------------------", f"-- {nombre}"]
    columnas = [
        f"  {col} {tipo}{' not null' if no_nulo else ''}{f' default {defecto}' if defecto else ''}"
        for col, tipo, no_nulo, defecto in cur.execute(CONSULTA_COLUMNAS, (nombre,)).fetchall()
    ]
    restricciones = [
        f"  constraint {n} {d}"
        for n, d in cur.execute(CONSULTA_RESTRICCIONES, (nombre,)).fetchall()
    ]
    lineas.append(f"create table {nombre} (\n" + ",\n".join(columnas + restricciones) + "\n);")
    lineas += [f"{d};" for _, d in cur.execute(CONSULTA_INDICES, (tabla, nombre)).fetchall()]
    if con_rls:
        lineas.append(f"alter table {nombre} enable row level security;")
    for pol, cmd, roles, permisiva, using, check in cur.execute(
        CONSULTA_POLITICAS, (tabla,)
    ).fetchall():
        lineas.append(
            f'-- politica "{pol}": {cmd} para {roles} ({permisiva})'
            f"{f' using ({using})' if using else ''}{f' with check ({check})' if check else ''}"
        )
    for rol, privilegios in cur.execute(CONSULTA_PRIVILEGIOS, (tabla,)).fetchall():
        lineas.append(f"-- privilegios de {rol}: {privilegios}")
    return lineas


def main() -> None:
    destino = SALIDA / f"schema_real_{date.today():%Y%m%d}.sql"
    partes = [
        "-- =========================================================",
        "-- Inventario REAL del esquema public (solo lectura, generado).",
        "-- REFERENCIA. NO EJECUTAR. Generado por scripts/inventariar_esquema.py",
        "-- =========================================================",
    ]
    with psycopg.connect(url_conexion(), autocommit=False) as conexion:
        conexion.read_only = True
        with conexion.cursor() as cur:
            version = cur.execute("show server_version").fetchone()[0]
            partes.append(f"-- PostgreSQL {version}\n")
            for tabla, con_rls in cur.execute(CONSULTA_TABLAS).fetchall():
                partes += describir_tabla(cur, tabla, con_rls) + [""]
            partes.append("-- ---------------------------------------------------------")
            partes.append("-- Funciones de public")
            partes += [f"{d};" for (d,) in cur.execute(CONSULTA_FUNCIONES).fetchall()]
            partes.append("-- ---------------------------------------------------------")
            partes.append("-- Triggers (public y auth.users)")
            partes += [f"{d};" for (d,) in cur.execute(CONSULTA_TRIGGERS).fetchall()]
            partes.append("-- ---------------------------------------------------------")
            partes.append("-- Event triggers (base de datos completa)")
            partes += [
                f"-- {nombre}: on {evento} -> {funcion} (estado {estado}; tags: {tags or '-'})"
                for nombre, evento, funcion, estado, tags in cur.execute(
                    CONSULTA_EVENT_TRIGGERS
                ).fetchall()
            ]
        conexion.rollback()
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(partes) + "\n", encoding="utf-8")
    print(f"Inventario escrito en {destino}")


if __name__ == "__main__":
    main()

"""limites de longitud y rango en los campos que escriben las personas

HU: HU-B-320
Revision ID: 0013
Revises: 0012
Create Date: 2026-10-24 11:00:00+00:00
Tipo: esquema
Destructiva: no

La base aplica los mismos limites que la API (app/core/longitudes.py) y el frontend
(contrato de API, seccion 7). Datos de produccion medidos el 2026-10-24: todas las filas
cumplen. Si alguna incumpliera, PostgreSQL aborta la revision completa sin cambiar nada.
`ck_*_duracion_min` se reemplaza (> 0 pasa a 1..600): no borra datos.
handle_new_user() normaliza el nombre para que un registro sin nombre (o con uno
invalido) no falle por los nuevos CHECK de profiles.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | Sequence[str] | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LIMITES = {
    "profiles": {
        "nombre": "char_length(btrim(nombre)) BETWEEN 2 AND 80",
        "nombre_sin_control": "nombre !~ '[[:cntrl:]]'",
    },
    "bloques": {
        "titulo": "char_length(btrim(titulo)) BETWEEN 3 AND 120",
        "descripcion": "char_length(descripcion) <= 2000",
    },
    "lecciones": {
        "titulo": "char_length(btrim(titulo)) BETWEEN 3 AND 120",
        "descripcion": "char_length(descripcion) <= 2000",
        "contenido": "char_length(contenido) <= 20000",
        "acordes": "cardinality(acordes) <= 24",
        "temas": "cardinality(temas) <= 20",
    },
    "ejercicios": {
        "nombre": "char_length(btrim(nombre)) BETWEEN 3 AND 120",
        "descripcion": "char_length(descripcion) <= 2000",
        "bpm_recomendado": "bpm_recomendado IS NULL OR "
        "(bpm_recomendado >= 20 AND bpm_recomendado <= 300)",
        "compas": "compas ~ '^(2|3|4|5|6|7|9|12)/(2|4|8)$'",
        "acordes": "cardinality(acordes) <= 24",
        "pasos": "cardinality(pasos) <= 30",
    },
    "acordes": {
        "nombre": "char_length(btrim(nombre)) BETWEEN 1 AND 20",
        "descripcion": "char_length(descripcion) <= 500",
    },
    "cursos": {"descripcion": "char_length(descripcion) <= 2000"},
}
TABLAS_CON_DURACION = ("lecciones", "ejercicios")
DURACION_ANTERIOR = "duracion_min IS NULL OR duracion_min > 0"
DURACION_NUEVA = "duracion_min IS NULL OR (duracion_min >= 1 AND duracion_min <= 600)"

# Nombre: espacios colapsados, maximo 80; sin nombre usable -> parte local del correo;
# si aun asi tiene menos de 2 caracteres -> 'Usuario'. search_path vacio: funcion
# SECURITY DEFINER sin riesgo de suplantacion de objetos.
FUNCION_NUEVA = """
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_nombre text;
begin
  v_nombre := regexp_replace(
    coalesce(new.raw_user_meta_data->>'nombre', ''), '[[:space:][:cntrl:]]+', ' ', 'g');
  v_nombre := btrim(v_nombre);
  if char_length(v_nombre) < 2 then
    v_nombre := btrim(split_part(coalesce(new.email, ''), '@', 1));
  end if;
  v_nombre := btrim(left(v_nombre, 80));
  if char_length(v_nombre) < 2 then
    v_nombre := 'Usuario';
  end if;
  insert into public.profiles (id, nombre, nivel) values (new.id, v_nombre, 'principiante');
  return new;
end;
$function$
"""
FUNCION_ANTERIOR = """
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
as $function$
begin
  insert into public.profiles (id, nombre, nivel)
  values (new.id, coalesce(new.raw_user_meta_data->>'nombre', new.email), 'principiante');
  return new;
end;
$function$
"""


def upgrade() -> None:
    op.execute(FUNCION_NUEVA)
    for tabla in TABLAS_CON_DURACION:
        # destructivo-aprobado: HU-B-320 (reemplaza un CHECK por uno mas estricto; sin datos)
        op.drop_constraint(op.f(f"ck_{tabla}_duracion_min"), tabla, type_="check")
        op.create_check_constraint(op.f(f"ck_{tabla}_duracion_min"), tabla, DURACION_NUEVA)
    for tabla, limites in LIMITES.items():
        for nombre, expresion in limites.items():
            op.create_check_constraint(op.f(f"ck_{tabla}_{nombre}"), tabla, expresion)


def downgrade() -> None:
    for tabla, limites in LIMITES.items():
        for nombre in limites:
            op.drop_constraint(op.f(f"ck_{tabla}_{nombre}"), tabla, type_="check")
    for tabla in TABLAS_CON_DURACION:
        op.drop_constraint(op.f(f"ck_{tabla}_duracion_min"), tabla, type_="check")
        op.create_check_constraint(op.f(f"ck_{tabla}_duracion_min"), tabla, DURACION_ANTERIOR)
    op.execute(FUNCION_ANTERIOR)
    # create or replace no quita el SET de la version nueva: se retira explicitamente.
    op.execute("alter function public.handle_new_user() reset search_path")

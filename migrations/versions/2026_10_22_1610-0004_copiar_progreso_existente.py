"""copiar progreso existente a progreso_lecciones y progreso_ejercicios

HU: HU-B-305
Revision ID: 0004
Revises: 0003
Create Date: 2026-10-22 16:10:00+00:00
Tipo: datos
Destructiva: no

- Copia las filas de `progreso` con tipo 'leccion' y 'ejercicio' cuyo contenido y
  perfil existen. Las huerfanas se cuentan (RAISE NOTICE) y se dejan en `progreso`.
- NO borra nada de `progreso` (se elimina en HU-B-312).
- Idempotente: ON CONFLICT DO NOTHING; se puede reejecutar su SQL sin duplicar.
- downgrade(): devuelve a `progreso` lo que se registro en las tablas nuevas
  (para no perder avances al revertir) y vacia las tablas nuevas.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (tipo en progreso, tabla nueva, columna del contenido, tabla del contenido)
DESTINOS = (
    ("leccion", "progreso_lecciones", "leccion_id", "lecciones"),
    ("ejercicio", "progreso_ejercicios", "ejercicio_id", "ejercicios"),
)

COPIAR = """
do $$
declare
  copiadas integer;
  huerfanas integer;
begin
  insert into public.{tabla} (estudiante_id, {columna}, porcentaje, completado,
                              creado_en, actualizado_en)
  select p.usuario_id, p.contenido_id, p.porcentaje, coalesce(p.completado, false),
         coalesce(p.actualizado_en, now()), coalesce(p.actualizado_en, now())
  from public.progreso p
  join public.{contenido} c on c.id = p.contenido_id
  join public.profiles pr on pr.id = p.usuario_id
  where p.tipo = '{tipo}'
  on conflict do nothing;
  get diagnostics copiadas = row_count;

  select count(*) into huerfanas
  from public.progreso p
  where p.tipo = '{tipo}'
    and (not exists (select 1 from public.{contenido} c where c.id = p.contenido_id)
         or not exists (select 1 from public.profiles pr where pr.id = p.usuario_id));

  raise notice '{tabla}: % fila(s) copiada(s), % huerfana(s) ignorada(s)', copiadas, huerfanas;
end $$
"""

DEVOLVER = """
insert into public.progreso (usuario_id, tipo, contenido_id, porcentaje, completado,
                             actualizado_en)
select n.estudiante_id, '{tipo}', n.{columna}, n.porcentaje, n.completado, n.actualizado_en
from public.{tabla} n
on conflict (usuario_id, tipo, contenido_id) do update
  set porcentaje = excluded.porcentaje,
      completado = excluded.completado,
      actualizado_en = excluded.actualizado_en
"""


def upgrade() -> None:
    for tipo, tabla, columna, contenido in DESTINOS:
        op.execute(COPIAR.format(tipo=tipo, tabla=tabla, columna=columna, contenido=contenido))


def downgrade() -> None:
    for tipo, tabla, columna, _ in DESTINOS:
        op.execute(DEVOLVER.format(tipo=tipo, tabla=tabla, columna=columna))
        op.execute(sa.delete(sa.table(tabla, schema="public")))

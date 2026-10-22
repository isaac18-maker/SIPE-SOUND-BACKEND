"""Respaldo de los DATOS del esquema public en JSON (HU-B-316, protección P10).

Alternativa a `pg_dump` cuando no esta instalado. El esquema no se respalda aqui:
lo reconstruyen las migraciones (`alembic upgrade head`).

Uso:
    uv run python -m scripts.respaldar_datos

Salida: respaldos/<AAAAMMDD_HHMMSS>/<tabla>.json y manifiesto.json (filas por tabla
y revision de Alembic). La carpeta respaldos/ esta en .gitignore: contiene datos
personales de estudiantes, nunca se sube al repositorio.

Seguridad: transaccion de SOLO LECTURA con REPEATABLE READ, todas las tablas salen
de la misma foto de la base.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from app.core.config import get_settings

CARPETA = Path("respaldos")
TABLAS = """
select tablename from pg_tables where schemaname = 'public' order by tablename
"""


def main() -> int:
    marca = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    destino = CARPETA / marca
    destino.mkdir(parents=True, exist_ok=False)
    manifiesto: dict = {"creado_en_utc": marca, "tablas": {}}

    with psycopg.connect(get_settings().url_base_de_datos(), row_factory=dict_row) as conexion:
        conexion.read_only = True
        conexion.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        with conexion.transaction():
            tablas = [fila["tablename"] for fila in conexion.execute(TABLAS).fetchall()]
            for tabla in tablas:
                consulta = sql.SQL("select * from public.{}").format(sql.Identifier(tabla))
                filas = conexion.execute(consulta).fetchall()
                (destino / f"{tabla}.json").write_text(
                    json.dumps(filas, ensure_ascii=False, indent=1, default=str),
                    encoding="utf-8",
                )
                manifiesto["tablas"][tabla] = len(filas)
                if tabla == "alembic_version" and filas:
                    manifiesto["revision_alembic"] = filas[0]["version_num"]

    (destino / "manifiesto.json").write_text(
        json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total = sum(manifiesto["tablas"].values())
    print(f"Respaldo en {destino}: {len(manifiesto['tablas'])} tablas, {total} filas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Guardia de migraciones (contrato de BD, protecciones P3 y P9).

Falla (codigo 1) si alguna revision de migrations/versions/:
- no declara en su cabecera "HU: HU-B-NNN" ni "Tipo: esquema|datos";
- tiene un downgrade() vacio (solo pass/docstring);
- en upgrade() usa op.drop_* u op.execute con DROP/TRUNCATE/DELETE sin la marca
  "# destructivo-aprobado: HU-X-NNN" en la misma linea o en la anterior;
o si la historia tiene mas de una head.

Uso: uv run python scripts/check_migrations.py
"""

import ast
import re
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

CARPETA = Path("migrations/versions")
PATRON_HU = re.compile(r"^HU:\s*HU-[BF]-\d{3}\s*$", re.MULTILINE)
PATRON_TIPO = re.compile(r"^Tipo:\s*(esquema|datos)\s*$", re.MULTILINE)
PATRON_MARCA = re.compile(r"#\s*destructivo-aprobado:\s*HU-[BF]-\d{3}")
PATRON_SQL_DESTRUCTIVO = re.compile(r"\b(DROP|TRUNCATE|DELETE)\b", re.IGNORECASE)


def _funcion(arbol: ast.Module, nombre: str) -> ast.FunctionDef | None:
    return next(
        (n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == nombre), None
    )


def _es_vacia(funcion: ast.FunctionDef) -> bool:
    utiles = [
        n
        for n in funcion.body
        if not isinstance(n, ast.Pass)
        and not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
    ]
    return not utiles


def _es_destructiva(llamada: ast.Call) -> bool:
    funcion = llamada.func
    if not (
        isinstance(funcion, ast.Attribute)
        and isinstance(funcion.value, ast.Name)
        and funcion.value.id == "op"
    ):
        return False
    if funcion.attr.startswith("drop_"):
        return True
    if funcion.attr == "execute" and llamada.args:
        sql = ast.unparse(llamada.args[0])
        return bool(PATRON_SQL_DESTRUCTIVO.search(sql))
    return False


def _tiene_marca(lineas: list[str], llamada: ast.Call) -> bool:
    desde = max(llamada.lineno - 2, 0)
    return any(PATRON_MARCA.search(linea) for linea in lineas[desde : llamada.end_lineno])


def revisar(archivo: Path) -> list[str]:
    codigo = archivo.read_text(encoding="utf-8")
    arbol = ast.parse(codigo)
    lineas = codigo.splitlines()
    cabecera = ast.get_docstring(arbol) or ""
    problemas = []
    if not PATRON_HU.search(cabecera):
        problemas.append("la cabecera no tiene 'HU: HU-B-NNN' (quedo 'HU-B-XXX'?)")
    if not PATRON_TIPO.search(cabecera):
        problemas.append("la cabecera no tiene 'Tipo: esquema' o 'Tipo: datos'")

    downgrade = _funcion(arbol, "downgrade")
    if downgrade is None or _es_vacia(downgrade):
        problemas.append("downgrade() esta vacio: debe revertir el upgrade")

    upgrade = _funcion(arbol, "upgrade")
    if upgrade is not None:
        for nodo in ast.walk(upgrade):
            es_call = isinstance(nodo, ast.Call)
            if es_call and _es_destructiva(nodo) and not _tiene_marca(lineas, nodo):
                problemas.append(
                    f"linea {nodo.lineno}: operacion destructiva sin "
                    "'# destructivo-aprobado: HU-B-NNN'"
                )
    return problemas


def revisar_heads() -> list[str]:
    heads = ScriptDirectory.from_config(Config("alembic.ini")).get_heads()
    if len(heads) > 1:
        return [f"hay {len(heads)} heads ({', '.join(heads)}): resuelvelo con 'alembic merge'"]
    return []


def main() -> int:
    archivos = sorted(CARPETA.glob("*.py"))
    errores = {str(a): p for a in archivos if (p := revisar(a))}
    heads = revisar_heads()
    for archivo, problemas in errores.items():
        print(f"[ERROR] {archivo}")
        for problema in problemas:
            print(f"    - {problema}")
    for problema in heads:
        print(f"[ERROR] historia de migraciones: {problema}")
    if errores or heads:
        return 1
    print(f"[OK] {len(archivos)} revision(es) revisada(s), una sola head. Sin problemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

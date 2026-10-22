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
# Sentencias que EMPIEZAN por DROP/TRUNCATE/DELETE (al inicio o tras ";"). Asi
# "revoke truncate on ..." (quitar un permiso) no cuenta como destructivo.
PATRON_SQL_DESTRUCTIVO = re.compile(
    r"(?:^|;)\s*(?:DROP|TRUNCATE|DELETE)\b", re.IGNORECASE | re.MULTILINE
)


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


def _literales(nodo: ast.AST) -> list[str]:
    """Textos de una constante de modulo: "…", ("…", "…") o ["…"]."""
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return [nodo.value]
    if isinstance(nodo, ast.Tuple | ast.List):
        return [texto for elemento in nodo.elts for texto in _literales(elemento)]
    return []


def _constantes(arbol: ast.Module) -> dict[str, list[str]]:
    constantes = {}
    for nodo in arbol.body:
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1:
            destino = nodo.targets[0]
            if isinstance(destino, ast.Name) and (textos := _literales(nodo.value)):
                constantes[destino.id] = textos
    return constantes


def _textos_sql(nodo: ast.AST, contexto: dict) -> list[str]:
    """SQL posible de un argumento de op.execute, resolviendo constantes del modulo,
    variables de bucle, .format() y f-strings (los valores interpolados valen "x")."""
    if isinstance(nodo, ast.Name):
        iterable = contexto["bucles"].get(nodo.id)
        if iterable is not None:
            return _textos_sql(iterable, contexto)
        return contexto["constantes"].get(nodo.id, [])
    if isinstance(nodo, ast.Tuple | ast.List):
        return [texto for elemento in nodo.elts for texto in _textos_sql(elemento, contexto)]
    es_format = isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
    if es_format and nodo.func.attr == "format":
        return _textos_sql(nodo.func.value, contexto)
    return [_texto_directo(nodo)]


def _texto_directo(nodo: ast.AST) -> str:
    if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
        return nodo.value
    if isinstance(nodo, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "x" for v in nodo.values)
    return ast.unparse(nodo)


def _es_destructiva(llamada: ast.Call, contexto: dict) -> bool:
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
        textos = _textos_sql(llamada.args[0], contexto)
        return any(PATRON_SQL_DESTRUCTIVO.search(texto) for texto in textos)
    return False


def _alcanzables_desde_upgrade(arbol: ast.Module) -> list[ast.FunctionDef]:
    """upgrade() y las funciones del modulo que llama (directa o indirectamente)."""
    funciones = {n.name: n for n in arbol.body if isinstance(n, ast.FunctionDef)}
    pendientes, vistas = ["upgrade"], []
    while pendientes:
        nombre = pendientes.pop()
        if nombre not in funciones or funciones[nombre] in vistas or nombre == "downgrade":
            continue
        vistas.append(funciones[nombre])
        pendientes += [
            n.func.id
            for n in ast.walk(funciones[nombre])
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        ]
    return vistas


def _bucles(funciones: list[ast.FunctionDef]) -> dict[str, ast.AST]:
    """Variable de bucle -> iterable (for sentencia in OCULTAR: op.execute(sentencia))."""
    return {
        n.target.id: n.iter
        for funcion in funciones
        for n in ast.walk(funcion)
        if isinstance(n, ast.For) and isinstance(n.target, ast.Name)
    }


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

    funciones = _alcanzables_desde_upgrade(arbol)
    contexto = {"constantes": _constantes(arbol), "bucles": _bucles(funciones)}
    for funcion in funciones:
        for nodo in ast.walk(funcion):
            es_call = isinstance(nodo, ast.Call)
            if es_call and _es_destructiva(nodo, contexto) and not _tiene_marca(lineas, nodo):
                problemas.append(
                    f"linea {nodo.lineno} ({funcion.name}): operacion destructiva sin "
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

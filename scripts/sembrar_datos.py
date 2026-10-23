"""Reemplaza el contenido de la base por la semilla de HU-B-326.

BORRA el contenido y su actividad (bloques, lecciones, ejercicios, evaluaciones, intentos, cursos,
inscripciones, retroalimentaciones y progreso) e inserta la ruta de scripts/semilla. Conserva las
cuentas, los perfiles y el catalogo de acordes.

Antes de ejecutarlo: `uv run python -m scripts.respaldar_datos`.

Uso:
    uv run python -m scripts.sembrar_datos --admin correo@dominio.co --confirmar borrar-contenido

Todo ocurre en UNA transaccion: si algo falla, la base queda como estaba. Las contrasenas de las
cuentas de prueba se generan al ejecutarlo y se muestran una sola vez.
"""

import argparse
import secrets
import string
import sys

from app.infrastructure.database import session_scope
from scripts.semilla import sql
from scripts.semilla.contenido import BLOQUES
from scripts.semilla.cursos import CURSOS, DOCENTE_PRUEBA, ESTUDIANTE_PRUEBA, PROGRESO_DEMO

CONFIRMACION = "borrar-contenido"


def contrasena() -> str:
    """16 caracteres con letras y numeros (regla de RegistroIn)."""
    alfabeto = string.ascii_letters + string.digits
    while True:
        valor = "".join(secrets.choice(alfabeto) for _ in range(16))
        if any(c.isdigit() for c in valor) and any(c.isalpha() for c in valor):
            return valor


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--admin", required=True, help="correo de la cuenta existente a promover")
    parser.add_argument("--confirmar", required=True, help=f"escribe '{CONFIRMACION}'")
    args = parser.parse_args()
    if args.confirmar != CONFIRMACION:
        print(f"No se hizo nada: --confirmar debe ser '{CONFIRMACION}'.", file=sys.stderr)
        return 1

    claves = {"docente": contrasena(), "estudiante": contrasena()}
    with session_scope() as sesion:
        print("Antes:", sql.conteos(sesion))
        admin_id = sql.promover_admin(sesion, args.admin)
        sql.vaciar_contenido(sesion)
        docente_id = sql.cuenta_de_prueba(
            sesion, DOCENTE_PRUEBA, claves["docente"], "docente", admin_id
        )
        estudiante_id = sql.cuenta_de_prueba(
            sesion, ESTUDIANTE_PRUEBA, claves["estudiante"], "estudiante", admin_id
        )
        ids = sql.insertar_ruta(sesion, BLOQUES, autor_id=admin_id)
        sql.insertar_cursos(sesion, CURSOS, ids, docente_id=docente_id, estudiante_id=estudiante_id)
        sql.insertar_progreso_demo(sesion, PROGRESO_DEMO, ids, estudiante_id=estudiante_id)
        print("Después:", sql.conteos(sesion))

    print("\nCuentas de prueba (guárdalas: no se vuelven a mostrar):")
    print(f"  Docente:    {DOCENTE_PRUEBA['email']} / {claves['docente']}")
    print(f"  Estudiante: {ESTUDIANTE_PRUEBA['email']} / {claves['estudiante']}")
    print(f"  Administrador: {args.admin} (su contraseña no cambia)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

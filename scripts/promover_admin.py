"""Asigna el rol 'admin' a un usuario existente (HU-B-304).

Sirve para crear el PRIMER administrador; los siguientes se asignan desde
PATCH /api/v1/admin/usuarios/{id}/rol.

Uso:
    uv run python -m scripts.promover_admin correo@dominio.co
    uv run python -m scripts.promover_admin correo@dominio.co --confirmar   # APP_ENV=production

Usa DATABASE_URL. Muestra el cambio antes de aplicarlo.
"""

import argparse
import sys

from sqlalchemy import text

from app.core.config import get_settings
from app.core.constants import ROL_ADMIN
from app.infrastructure.database import session_scope

BUSCAR = text(
    "select p.id, p.nombre, p.rol from auth.users u "
    "join public.profiles p on p.id = u.id where lower(u.email) = lower(:email)"
)
PROMOVER = text("update public.profiles set rol = :rol where id = :id")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email")
    parser.add_argument("--confirmar", action="store_true", help="obligatorio en produccion")
    args = parser.parse_args()

    motivo = get_settings().motivo_para_bloquear_operacion(confirmado=args.confirmar)
    if motivo:
        print(f"{motivo} En produccion, vuelve a ejecutar con --confirmar.")
        return 1

    with session_scope() as sesion:
        fila = sesion.execute(BUSCAR, {"email": args.email}).one_or_none()
        if fila is None:
            print(f"No hay un usuario registrado con el correo {args.email}.")
            return 1
        if fila.rol == ROL_ADMIN:
            print(f"{fila.nombre} ya es administrador. Sin cambios.")
            return 0
        sesion.execute(PROMOVER, {"rol": ROL_ADMIN, "id": fila.id})
        print(f"{fila.nombre}: {fila.rol} -> {ROL_ADMIN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Envia un correo de prueba con la plantilla de verificacion (HU-B-401).

Sirve para comprobar el SMTP de Gmail y ver como llega la plantilla en cada cliente de
correo. El codigo es 000000 y el correo dice que es de prueba.

Uso:
    uv run python -m scripts.probar_correo --para tu@correo.co
    uv run python -m scripts.probar_correo --para tu@correo.co --confirmar   # APP_ENV=production

Con CORREO_MODO=archivo (solo local) deja un .eml en tmp/correos/ en lugar de enviarlo.
Usa DATABASE_URL para anotar el resultado en envios_correo.
"""

import argparse
import sys

from app.container import correo_service
from app.core.config import get_settings
from app.core.constants import CORREO_VERIFICAR

CONTEXTO_PRUEBA = {
    "nombre": "Prueba",
    "codigo": "000000",
    "minutos": 1,
    "enlace": "http://localhost:5173/verificar?email=prueba%40ejemplo.co",
    "prueba": True,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--para", required=True, help="correo que recibe la prueba")
    parser.add_argument("--confirmar", action="store_true", help="obligatorio en produccion")
    args = parser.parse_args()

    ajustes = get_settings()
    motivo = ajustes.motivo_para_bloquear_operacion(confirmado=args.confirmar)
    if motivo:
        print(f"{motivo} En produccion, vuelve a ejecutar con --confirmar.")
        return 1

    error = correo_service().enviar_ahora(CORREO_VERIFICAR, args.para, CONTEXTO_PRUEBA)
    if error:
        print(
            f"No se pudo enviar el correo ({error}). Revisa SMTP_USUARIO y SMTP_CLAVE_APLICACION."
        )
        return 1
    destino = "tmp/correos/" if ajustes.modo_correo == "archivo" else args.para
    print(f"Correo de prueba entregado ({ajustes.modo_correo}): {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

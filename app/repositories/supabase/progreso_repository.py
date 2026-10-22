# =========================================================
# Progreso del usuario via REST con su propio token (RLS).
# =========================================================
from app.core.errors import ErrorProveedor
from app.infrastructure.supabase_rest import supabase_rest
from app.repositories.base import Fila

CONFLICTO_UPSERT = "usuario_id,tipo,contenido_id"


class SupabaseProgresoRepository:
    def listar(self, usuario_id: str, token: str) -> list[Fila]:
        return _ejecutar("GET", token, params={"usuario_id": f"eq.{usuario_id}"})

    def obtener(self, usuario_id: str, tipo: str, contenido_id: int, token: str) -> Fila | None:
        filas = _ejecutar(
            "GET",
            token,
            params={
                "usuario_id": f"eq.{usuario_id}",
                "tipo": f"eq.{tipo}",
                "contenido_id": f"eq.{contenido_id}",
            },
        )
        return filas[0] if filas else None

    def guardar(self, registro: Fila, token: str) -> list[Fila]:
        return _ejecutar(
            "POST", token, params={"on_conflict": CONFLICTO_UPSERT}, json_body=registro
        )


def _ejecutar(metodo: str, token: str, **kwargs) -> list[Fila]:
    respuesta = supabase_rest(metodo, "progreso", token, **kwargs)
    if respuesta.status_code >= 400:  # noqa: PLR2004 - rango de errores HTTP
        # TODO(HU-B-204): no reenviar el texto del proveedor al cliente.
        raise ErrorProveedor(respuesta.text, status=respuesta.status_code)
    return respuesta.json()

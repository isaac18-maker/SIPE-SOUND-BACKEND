# =========================================================
# Alta de docentes sin claves de Supabase (HU-B-321):
#   1. el admin preautoriza el correo (POST /admin/docentes/preautorizaciones);
#   2. la persona se registra como cualquier estudiante (Supabase Auth, frontend);
#   3. al CONFIRMAR su correo, la base le asigna el rol 'docente' (trigger, 0014).
# Si ya tenia una cuenta confirmada, el rol se asigna en el paso 1.
# =========================================================
from typing import Any, Protocol

from app.core.errors import Conflicto, NoEncontrado
from app.repositories.base import AbrirSesion, Fila


class RepositorioDocentes(Protocol):
    """Contrato que el servicio necesita; lo cumple SqlDocenteRepository."""

    def obtener(self, sesion: Any, email: str) -> Fila | None: ...
    def listar(self, sesion: Any) -> list[Fila]: ...
    def crear(self, sesion: Any, email: str, creado_por: str) -> Fila: ...
    def eliminar(self, sesion: Any, email: str) -> None: ...


def _con_estado(fila: Fila) -> Fila:
    return {**fila, "estado": "aplicada" if fila["usado_en"] else "pendiente"}


class DocenteService:
    def __init__(self, abrir_sesion: AbrirSesion, docentes: RepositorioDocentes) -> None:
        self._abrir_sesion = abrir_sesion
        self._docentes = docentes

    def preautorizar(self, email: str, admin_id: str) -> Fila:
        with self._abrir_sesion() as sesion:
            if self._docentes.obtener(sesion, email) is not None:
                raise Conflicto("Ese correo ya está preautorizado.")
            return _con_estado(self._docentes.crear(sesion, email, admin_id))

    def listar(self) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            return [_con_estado(f) for f in self._docentes.listar(sesion)]

    def revocar(self, email: str) -> None:
        """Solo las pendientes: una ya aplicada se revierte cambiando el rol del usuario."""
        with self._abrir_sesion() as sesion:
            fila = self._docentes.obtener(sesion, email)
            if fila is None:
                raise NoEncontrado("Ese correo no está preautorizado.")
            if fila["usado_en"] is not None:
                raise Conflicto(
                    "La preautorización ya se usó: cambia el rol con "
                    "PATCH /admin/usuarios/{id}/rol."
                )
            self._docentes.eliminar(sesion, email)

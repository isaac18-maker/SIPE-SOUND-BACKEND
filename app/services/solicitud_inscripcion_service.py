# =========================================================
# Solicitudes de inscripcion a cursos (HU-B-414). El estudiante ve el catalogo de cursos y pide
# entrar; el docente del curso o un administrador la acepta (se crea la inscripcion) o la rechaza.
# Un curso sin docente solo lo resuelve un administrador. El codigo de invitacion sigue entrando
# directo (no pasa por aqui). Nunca devuelve correos.
# =========================================================
from typing import Any, Protocol

from sqlalchemy.exc import IntegrityError

from app.core.constants import ROL_ADMIN
from app.core.errors import Conflicto, NoEncontrado, ReglaNegocio
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, Fila

MENSAJE_YA_INSCRITO = "Ya estás inscrito en este curso."
MENSAJE_YA_PENDIENTE = "Ya enviaste una solicitud a este curso: espera la respuesta."
MENSAJE_YA_RESUELTA = "Esa solicitud ya fue resuelta."
MENSAJE_CURSO_ARCHIVADO = "El curso está archivado: ya no admite inscripciones."


class RepositorioSolicitudes(Protocol):
    def catalogo(self, sesion: Any, estudiante_id: str) -> list[Fila]: ...
    def listar(
        self, sesion: Any, docente_id: str | None, estado: str | None, curso_id: int | None
    ) -> list[Fila]: ...
    def totales(self, sesion: Any, docente_id: str | None) -> dict[str, int]: ...
    def obtener_para_resolver(self, sesion: Any, solicitud_id: str) -> Fila | None: ...
    def crear(self, sesion: Any, curso_id: int, estudiante_id: str) -> Fila: ...
    def resolver(self, sesion: Any, solicitud_id: str, estado: str, por: str) -> Fila | None: ...
    def cancelar(self, sesion: Any, curso_id: int, estudiante_id: str) -> bool: ...
    def esta_inscrito(self, sesion: Any, curso_id: int, estudiante_id: str) -> bool: ...
    def curso_activo(self, sesion: Any, curso_id: int) -> bool: ...


class RepositorioInscripciones(Protocol):
    def inscribir(self, sesion: Any, curso_id: int, estudiante_id: str) -> None: ...


class SolicitudInscripcionService:
    def __init__(
        self,
        abrir_sesion: AbrirSesion,
        solicitudes: RepositorioSolicitudes,
        cursos: RepositorioInscripciones,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._solicitudes = solicitudes
        self._cursos = cursos

    # --- Estudiante -------------------------------------------------------------------
    def catalogo(self, estudiante_id: str) -> list[Fila]:
        """Los cursos activos, cada uno con `mi_estado`: inscrito, pendiente, rechazada o None."""
        with self._abrir_sesion() as sesion:
            return self._solicitudes.catalogo(sesion, estudiante_id)

    def solicitar(self, estudiante_id: str, curso_id: int) -> Fila:
        with self._abrir_sesion() as sesion:
            if not self._solicitudes.curso_activo(sesion, curso_id):
                raise NoEncontrado(f"No existe el curso {curso_id}")
            if self._solicitudes.esta_inscrito(sesion, curso_id, estudiante_id):
                raise Conflicto(MENSAJE_YA_INSCRITO)
            try:
                with sesion.begin_nested():  # savepoint: la unica pendiente puede colisionar
                    return self._solicitudes.crear(sesion, curso_id, estudiante_id)
            except IntegrityError as error:
                raise Conflicto(MENSAJE_YA_PENDIENTE) from error

    def cancelar(self, estudiante_id: str, curso_id: int) -> None:
        with self._abrir_sesion() as sesion:
            if not self._solicitudes.cancelar(sesion, curso_id, estudiante_id):
                raise NoEncontrado("No tienes una solicitud pendiente en ese curso.")

    # --- Docente y administrador ---------------------------------------------------
    @staticmethod
    def _alcance(usuario: CurrentUser) -> str | None:
        """None = todas (administrador). Un docente solo las de sus cursos."""
        return None if usuario.rol == ROL_ADMIN else usuario.id

    def listar(
        self, usuario: CurrentUser, estado: str | None, curso_id: int | None
    ) -> tuple[list[Fila], dict[str, int]]:
        docente = self._alcance(usuario)
        with self._abrir_sesion() as sesion:
            filas = self._solicitudes.listar(sesion, docente, estado, curso_id)
            totales = self._solicitudes.totales(sesion, docente)
        return filas, totales

    def resolver(self, usuario: CurrentUser, solicitud_id: str, estado: str) -> Fila:
        """Acepta (crea la inscripcion) o rechaza. Ajena a tus cursos: 404, no 403."""
        with self._abrir_sesion() as sesion:
            solicitud = self._solicitudes.obtener_para_resolver(sesion, solicitud_id)
            es_suya = solicitud is not None and (
                usuario.rol == ROL_ADMIN or solicitud["docente_id"] == usuario.id
            )
            if not es_suya:
                raise NoEncontrado("No existe esa solicitud.")
            if solicitud["estado"] != "pendiente":
                raise Conflicto(MENSAJE_YA_RESUELTA)
            if estado == "aceptada" and solicitud["archivado_en"] is not None:
                raise ReglaNegocio(MENSAJE_CURSO_ARCHIVADO)
            resuelta = self._solicitudes.resolver(sesion, solicitud_id, estado, usuario.id)
            if resuelta is None:
                raise Conflicto(MENSAJE_YA_RESUELTA)
            if estado == "aceptada":
                self._cursos.inscribir(sesion, solicitud["curso_id"], solicitud["estudiante_id"])
            return resuelta

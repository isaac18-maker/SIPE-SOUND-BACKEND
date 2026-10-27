# =========================================================
# Actividad del docente (HU-B-418): se registra DESDE los servicios existentes, en la misma
# transaccion de la accion, y el admin la consulta para detectar a un docente inactivo.
# Registrar nunca rompe la accion del docente: va en un savepoint y un fallo solo se registra en
# el log. Solo se guarda el tipo de cosa y el curso, nunca el contenido.
# =========================================================
import logging
from datetime import date
from typing import Any, Protocol

from sqlalchemy.exc import SQLAlchemyError

from app.core.constants import (
    ACTIVIDAD_DIAS_DEFECTO,
    ACTIVIDAD_INICIO_CADA_MIN,
    ACTIVIDAD_LIMPIEZA_LOTE,
    ACTIVIDAD_RETENCION_DIAS,
    ROL_DOCENTE,
)
from app.core.errors import NoEncontrado
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, Fila

logger = logging.getLogger(__name__)


class RepositorioActividad(Protocol):
    def registrar(
        self, sesion: Any, docente_id: str, curso_id: int | None, tipo: str, accion: str
    ) -> None: ...
    def registrar_inicio(self, sesion: Any, docente_id: str, *, cada_minutos: int) -> bool: ...
    def limpiar(self, sesion: Any, *, dias: int, lote: int) -> int: ...
    def es_docente(self, sesion: Any, docente_id: str) -> bool: ...
    def listar(
        self,
        sesion: Any,
        *,
        q: str | None,
        estado_actividad: str | None,
        orden: str,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]: ...
    def resumen(self, sesion: Any, docente_id: str, dias: int) -> Fila: ...
    def linea_de_tiempo(
        self,
        sesion: Any,
        docente_id: str,
        *,
        tipo: str | None,
        curso_id: int | None,
        desde: date | None,
        hasta: date | None,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]: ...


class RegistroDeActividad(Protocol):
    """Lo que otros servicios necesitan: registrar dentro de SU sesion."""

    def registrar(
        self, sesion: Any, usuario: CurrentUser, tipo: str, accion: str, curso_id: int | None = None
    ) -> None: ...


class ActividadDocenteService:
    def __init__(self, abrir_sesion: AbrirSesion, actividad: RepositorioActividad) -> None:
        self._abrir_sesion = abrir_sesion
        self._actividad = actividad

    # --- Registro -------------------------------------------------------------------------
    def registrar(
        self, sesion: Any, usuario: CurrentUser, tipo: str, accion: str, curso_id: int | None = None
    ) -> None:
        """Una sentencia por accion, en la transaccion de quien llama. Solo docentes: lo que hace
        el admin queda en acciones_admin."""
        if usuario.rol != ROL_DOCENTE:
            return
        try:
            with sesion.begin_nested():  # savepoint: un fallo no aborta la accion del docente
                self._actividad.registrar(sesion, usuario.id, curso_id, tipo, accion)
        except SQLAlchemyError:
            logger.exception("No se pudo registrar la actividad del docente")

    def registrar_inicio_de_sesion(self, docente_id: str) -> None:
        """Como maximo uno por hora. Aprovecha para borrar, por lotes, lo de mas de 180 dias."""
        try:
            with self._abrir_sesion() as sesion:
                if self._actividad.registrar_inicio(
                    sesion, docente_id, cada_minutos=ACTIVIDAD_INICIO_CADA_MIN
                ):
                    self._actividad.limpiar(
                        sesion, dias=ACTIVIDAD_RETENCION_DIAS, lote=ACTIVIDAD_LIMPIEZA_LOTE
                    )
        except SQLAlchemyError:
            logger.exception("No se pudo registrar el inicio de sesion del docente")

    # --- Consulta del admin -----------------------------------------------------------------
    def listar(self, filtros: dict[str, Any]) -> tuple[list[Fila], int]:
        with self._abrir_sesion() as sesion:
            return self._actividad.listar(sesion, **filtros)

    def resumen(self, docente_id: str, dias: int = ACTIVIDAD_DIAS_DEFECTO) -> Fila:
        with self._abrir_sesion() as sesion:
            self._exigir_docente(sesion, docente_id)
            return self._actividad.resumen(sesion, docente_id, dias)

    def linea_de_tiempo(self, docente_id: str, filtros: dict[str, Any]) -> tuple[list[Fila], int]:
        with self._abrir_sesion() as sesion:
            self._exigir_docente(sesion, docente_id)
            return self._actividad.linea_de_tiempo(sesion, docente_id, **filtros)

    def _exigir_docente(self, sesion: Any, docente_id: str) -> None:
        if not self._actividad.es_docente(sesion, docente_id):
            raise NoEncontrado(f"No existe el docente {docente_id}")

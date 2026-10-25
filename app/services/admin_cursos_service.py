# =========================================================
# Administracion de docentes, cursos y accesos a cursos (HU-B-406).
#   - Ver los cursos de cada docente y reasignarlos a otro docente ACTIVO (la FK
#     cursos.docente_id es RESTRICT: un docente con cursos no se puede eliminar hasta
#     reasignarlos, ni siquiera los archivados).
#   - Revocar el acceso de un estudiante a un curso (o a todos): borra la inscripcion, nunca
#     el progreso del estudiante, que es suyo.
# Toda accion queda en acciones_admin. El admin ve el correo completo del estudiante.
# =========================================================
from typing import Any

from app.core.constants import CUENTA_ACTIVA, ROL_DOCENTE
from app.core.errors import NoEncontrado, ReglaNegocio
from app.repositories.base import (
    AbrirSesion,
    RepositorioAcciones,
    RepositorioAdminCuentas,
    RepositorioAdminDocentes,
    RepositorioCursos,
)
from app.services.curso_service import RepositorioSeguimiento

MENSAJE_DESTINO = "El curso solo puede pasar a un docente con la cuenta activa."
MENSAJE_MISMO_DOCENTE = "Ese curso ya está a cargo de ese docente."
SUGERENCIA_CODIGO = "Si compartió el código del curso, pídele al docente que lo regenere."


class AdminCursosService:
    def __init__(  # noqa: PLR0913, PLR0917 - dependencias inyectadas desde app/container.py
        self,
        abrir_sesion: AbrirSesion,
        docentes: RepositorioAdminDocentes,
        cuentas_admin: RepositorioAdminCuentas,
        cursos: RepositorioCursos,
        seguimiento: RepositorioSeguimiento,
        auditoria: RepositorioAcciones,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._docentes = docentes
        self._cuentas_admin = cuentas_admin
        self._cursos = cursos
        self._seguimiento = seguimiento
        self._auditoria = auditoria

    # --- Consulta -------------------------------------------------------------------------
    def listar_docentes(self, filtros: dict[str, Any]) -> tuple[list[dict], int]:
        with self._abrir_sesion() as sesion:
            return self._docentes.listar_docentes(sesion, **filtros)

    def cursos_de_docente(self, docente_id: str) -> list[dict]:
        with self._abrir_sesion() as sesion:
            self._exigir_docente(sesion, docente_id)
            return self._docentes.cursos_de_docente(sesion, docente_id)

    def listar_cursos(self, filtros: dict[str, Any]) -> tuple[list[dict], int]:
        with self._abrir_sesion() as sesion:
            return self._docentes.listar_cursos(sesion, **filtros)

    def estudiantes_de_curso(
        self, curso_id: int, filtros: dict[str, Any]
    ) -> tuple[list[dict], int]:
        """Igual que el listado del docente, pero con el correo COMPLETO (el admin lo necesita)."""
        with self._abrir_sesion() as sesion:
            self._curso(sesion, curso_id)
            return self._seguimiento.estudiantes(sesion, curso_id, **filtros)

    # --- Reasignar ------------------------------------------------------------------------
    def reasignar(self, admin_id: str, curso_id: int, docente_id: str) -> dict[str, Any]:
        with self._abrir_sesion() as sesion:
            curso = self._curso(sesion, curso_id, bloquear=True)
            destino = self._cuentas_admin.obtener(sesion, docente_id)
            if (
                destino is None
                or destino["rol"] != ROL_DOCENTE
                or destino["estado"] != CUENTA_ACTIVA
            ):
                raise ReglaNegocio(MENSAJE_DESTINO)
            origen = curso["docente_id"]
            if origen == docente_id:
                raise ReglaNegocio(MENSAJE_MISMO_DOCENTE)
            # Las evaluaciones del curso conservan su autor_id: el historial no cambia.
            actualizado = self._cursos.actualizar(sesion, curso_id, {"docente_id": docente_id})
            detalle = {
                "curso_id": curso_id,
                "curso": curso["nombre"],
                "de": origen,
                "a": docente_id,
            }
            # Una fila por cuenta afectada: cada una la ve en el detalle de su cuenta.
            for afectada in (origen, docente_id):
                self._auditoria.registrar(
                    sesion,
                    admin_id=admin_id,
                    usuario_id=afectada,
                    accion="reasignar_curso",
                    detalle=detalle,
                )
        return actualizado

    # --- Accesos ---------------------------------------------------------------------------
    def revocar_inscripcion(self, admin_id: str, curso_id: int, estudiante_id: str) -> None:
        with self._abrir_sesion() as sesion:
            curso = self._curso(sesion, curso_id, bloquear=True)
            if not self._cursos.retirar(sesion, curso_id, estudiante_id):
                raise NoEncontrado("Ese estudiante no está inscrito en el curso.")
            self._auditar_revocacion(sesion, admin_id, estudiante_id, curso)

    def revocar_todas(self, admin_id: str, estudiante_id: str) -> int:
        """Retira a la persona de todos sus cursos activos (p. ej. cambio de colegio)."""
        with self._abrir_sesion() as sesion:
            if self._cuentas_admin.obtener(sesion, estudiante_id) is None:
                raise NoEncontrado(f"No existe el usuario {estudiante_id}")
            inscripciones = self._cuentas_admin.inscripciones(sesion, estudiante_id)
            for inscripcion in inscripciones:
                curso = {"id": inscripcion["curso_id"], "nombre": inscripcion["curso"]}
                self._cursos.retirar(sesion, curso["id"], estudiante_id)
                self._auditar_revocacion(sesion, admin_id, estudiante_id, curso)
        return len(inscripciones)

    # --- Auxiliares -----------------------------------------------------------------------
    def _curso(self, sesion: Any, curso_id: int, *, bloquear: bool = False) -> dict[str, Any]:
        curso = self._cursos.obtener(sesion, curso_id, bloquear=bloquear)
        if curso is None:
            raise NoEncontrado(f"No existe el curso {curso_id}")
        return curso

    def _exigir_docente(self, sesion: Any, docente_id: str) -> None:
        cuenta = self._cuentas_admin.obtener(sesion, docente_id)
        if cuenta is None or cuenta["rol"] != ROL_DOCENTE:
            raise NoEncontrado(f"No existe el docente {docente_id}")

    def _auditar_revocacion(
        self, sesion: Any, admin_id: str, estudiante_id: str, curso: dict[str, Any]
    ) -> None:
        self._auditoria.registrar(
            sesion,
            admin_id=admin_id,
            usuario_id=estudiante_id,
            accion="revocar_curso",
            detalle={"curso_id": curso["id"], "curso": curso["nombre"]},
        )

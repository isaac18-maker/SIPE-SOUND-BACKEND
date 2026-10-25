# =========================================================
# Evaluaciones desde el panel docente (HU-B-311).
# - De curso: las gestiona el docente del curso (CursoService valida la propiedad).
# - De bloque (globales, sin curso): las crea y las borra solo un administrador; el docente ve,
#   edita y publica las de los bloques que recorren sus cursos (HU-B-412).
# - Borrar: solo quien la creo o un administrador (lo ajeno se cierra).
# - Preguntas: se reemplazan completas y solo si no hay intentos (consistencia).
# - Estados: TRANSICIONES es la unica fuente; no se publica sin preguntas.
# =========================================================
from typing import Any, Protocol

from app.core.constants import (
    EVALUACION_BORRADOR,
    EVALUACION_CERRADA,
    EVALUACION_PUBLICADA,
    ROL_ADMIN,
)
from app.core.errors import Conflicto, NoEncontrado, ReglaNegocio, SinPermiso
from app.core.security import CurrentUser
from app.repositories.base import AbrirSesion, Fila

MENSAJE_BORRAR_AJENA = (
    "Solo quien creó esta evaluación puede borrarla. Puedes cerrarla para que no se presente."
)

TRANSICIONES: dict[str, set[str]] = {
    EVALUACION_BORRADOR: {EVALUACION_PUBLICADA},
    EVALUACION_PUBLICADA: {EVALUACION_CERRADA},
    EVALUACION_CERRADA: set(),
}


class RepositorioGestionEvaluaciones(Protocol):
    def listar(
        self, sesion: Any, *, docente_id: str | None, curso_id: int | None, estado: str | None
    ) -> list[Fila]: ...
    def obtener(
        self, sesion: Any, evaluacion_id: int, *, bloquear: bool = False
    ) -> Fila | None: ...
    def preguntas(self, sesion: Any, evaluacion_id: int) -> list[Fila]: ...
    def crear(self, sesion: Any, datos: Fila) -> Fila: ...
    def actualizar(self, sesion: Any, evaluacion_id: int, cambios: Fila) -> Fila: ...
    def tiene_intentos(self, sesion: Any, evaluacion_id: int) -> bool: ...
    def contar_preguntas(self, sesion: Any, evaluacion_id: int) -> int: ...
    def reemplazar_preguntas(
        self, sesion: Any, evaluacion_id: int, preguntas: list[Fila]
    ) -> list[Fila]: ...
    def eliminar(self, sesion: Any, evaluacion_id: int) -> None: ...
    def global_en_alcance(self, sesion: Any, evaluacion_id: int, docente_id: str) -> bool: ...
    def resultados(self, sesion: Any, evaluacion: Fila, docente_id: str | None = None) -> Fila: ...


class PropiedadCurso(Protocol):
    def curso_propio(
        self, sesion: Any, usuario: CurrentUser, curso_id: int, *, activo: bool = False
    ) -> Fila: ...


class GestionEvaluacionService:
    def __init__(
        self,
        abrir_sesion: AbrirSesion,
        evaluaciones: RepositorioGestionEvaluaciones,
        cursos: PropiedadCurso,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._evaluaciones = evaluaciones
        self._cursos = cursos

    def listar(self, usuario: CurrentUser, filtros: dict[str, Any]) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            if filtros.get("curso_id") is not None:
                self._cursos.curso_propio(sesion, usuario, filtros["curso_id"])
            docente = None if _es_admin(usuario) else usuario.id
            return self._evaluaciones.listar(sesion, docente_id=docente, **filtros)

    def obtener(self, usuario: CurrentUser, evaluacion_id: int) -> Fila:
        """Incluye las preguntas CON la respuesta correcta (vista del docente)."""
        with self._abrir_sesion() as sesion:
            evaluacion = self._propia(sesion, usuario, evaluacion_id)
            return {
                **evaluacion,
                "preguntas": self._evaluaciones.preguntas(sesion, evaluacion_id),
                "tiene_intentos": self._evaluaciones.tiene_intentos(sesion, evaluacion_id),
            }

    def crear(self, usuario: CurrentUser, datos: Fila) -> Fila:
        with self._abrir_sesion() as sesion:
            if datos.get("curso_id") is None and not _es_admin(usuario):
                raise SinPermiso("Solo un administrador crea evaluaciones de bloque (globales).")
            if datos.get("curso_id") is not None:
                self._cursos.curso_propio(sesion, usuario, datos["curso_id"], activo=True)
            return self._evaluaciones.crear(
                sesion, {**datos, "autor_id": usuario.id, "estado": EVALUACION_BORRADOR}
            )

    def actualizar(self, usuario: CurrentUser, evaluacion_id: int, cambios: Fila) -> Fila:
        with self._abrir_sesion() as sesion:
            self._propia(sesion, usuario, evaluacion_id, bloquear=True)
            if "porcentaje_aprobacion" in cambios and self._evaluaciones.tiene_intentos(
                sesion, evaluacion_id
            ):
                raise ReglaNegocio(
                    "Ya hay intentos: cambiar el porcentaje de aprobación alteraría resultados "
                    "pasados. Duplica la evaluación."
                )
            return self._evaluaciones.actualizar(
                sesion, evaluacion_id, {**cambios, "actualizado_por": usuario.id}
            )

    def reemplazar_preguntas(
        self, usuario: CurrentUser, evaluacion_id: int, preguntas: list[Fila]
    ) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            self._propia(sesion, usuario, evaluacion_id, bloquear=True)
            if self._evaluaciones.tiene_intentos(sesion, evaluacion_id):
                raise ReglaNegocio(
                    "Ya hay intentos: para cambiar las preguntas, duplica la evaluación."
                )
            self._evaluaciones.actualizar(sesion, evaluacion_id, {"actualizado_por": usuario.id})
            return self._evaluaciones.reemplazar_preguntas(sesion, evaluacion_id, preguntas)

    def cambiar_estado(self, usuario: CurrentUser, evaluacion_id: int, estado: str) -> Fila:
        with self._abrir_sesion() as sesion:
            actual = self._propia(sesion, usuario, evaluacion_id, bloquear=True)
            if actual["estado"] == estado:
                return actual
            if estado not in TRANSICIONES[actual["estado"]]:
                raise ReglaNegocio(f"No se puede pasar de {actual['estado']} a {estado}.")
            if estado == EVALUACION_PUBLICADA and not self._evaluaciones.contar_preguntas(
                sesion, evaluacion_id
            ):
                raise ReglaNegocio("Agrega al menos una pregunta antes de publicar.")
            return self._evaluaciones.actualizar(
                sesion, evaluacion_id, {"estado": estado, "actualizado_por": usuario.id}
            )

    def eliminar(self, usuario: CurrentUser, evaluacion_id: int) -> None:
        with self._abrir_sesion() as sesion:
            evaluacion = self._propia(sesion, usuario, evaluacion_id, bloquear=True)
            if not _es_admin(usuario) and evaluacion["autor_id"] != usuario.id:
                raise SinPermiso(MENSAJE_BORRAR_AJENA)
            if self._evaluaciones.tiene_intentos(sesion, evaluacion_id):
                raise Conflicto(
                    "La evaluación tiene intentos de estudiantes. Ciérrala en lugar de borrarla.",
                    details=[{"campo": "sugerencia", "mensaje": "cerrar"}],
                )
            self._evaluaciones.eliminar(sesion, evaluacion_id)

    def resultados(self, usuario: CurrentUser, evaluacion_id: int) -> Fila:
        with self._abrir_sesion() as sesion:
            evaluacion = self._propia(sesion, usuario, evaluacion_id)
            # Una global reúne a todos los cursos: el docente solo ve a sus propios estudiantes.
            ajena = evaluacion["curso_id"] is None and not _es_admin(usuario)
            datos = self._evaluaciones.resultados(sesion, evaluacion, usuario.id if ajena else None)
        cifras = datos["cifras"]
        del_curso = cifras["estudiantes_del_curso"] if evaluacion["curso_id"] else None
        presentaron = cifras["estudiantes_que_presentaron"]
        return {
            "evaluacion_id": evaluacion_id,
            "minimo_requerido": evaluacion["porcentaje_aprobacion"],
            "intentos": cifras["intentos"],
            "estudiantes_que_presentaron": presentaron,
            "estudiantes_del_curso": del_curso,
            "promedio_mejor_puntaje": _entero(cifras["promedio_mejor_puntaje"]),
            "aprobaron_pct": (
                round(cifras["estudiantes_aprobados"] * 100 / presentaron) if presentaron else None
            ),
            "preguntas": [
                {**p, "aciertos_pct": _entero(p["aciertos_pct"])} for p in datos["preguntas"]
            ],
            "estudiantes": datos["estudiantes"],
            "sin_presentar": datos["sin_presentar"],
        }

    # --- Privados ---------------------------------------------------------------
    def _propia(
        self, sesion: Any, usuario: CurrentUser, evaluacion_id: int, *, bloquear: bool = False
    ) -> Fila:
        """De curso: la de su docente. Global: el admin o el docente de un curso que la recorre."""
        evaluacion = self._evaluaciones.obtener(sesion, evaluacion_id, bloquear=bloquear)
        if evaluacion is not None:
            if evaluacion["curso_id"] is None and (
                _es_admin(usuario)
                or self._evaluaciones.global_en_alcance(sesion, evaluacion_id, usuario.id)
            ):
                return evaluacion
            if evaluacion["curso_id"] is not None:
                try:
                    self._cursos.curso_propio(sesion, usuario, evaluacion["curso_id"])
                except NoEncontrado:
                    pass
                else:
                    return evaluacion
        raise NoEncontrado(f"No existe la evaluación {evaluacion_id}")


def _es_admin(usuario: CurrentUser) -> bool:
    return usuario.rol == ROL_ADMIN


def _entero(valor: Any) -> int | None:
    return None if valor is None else int(valor)

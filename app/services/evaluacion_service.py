# =========================================================
# Evaluaciones del estudiante (HU-B-308).
# - La respuesta correcta NUNCA sale antes de enviar el intento.
# - Cada intento se guarda (aprobado o no); el mejor puntaje se calcula.
# - Reglas: estado, fecha_limite, intentos_max y bloque desbloqueado -> 422.
# =========================================================
from datetime import UTC, datetime
from typing import Any, Protocol

from app.core.constants import EVALUACION_CERRADA, EVALUACION_PUBLICADA
from app.core.errors import NoEncontrado, ReglaNegocio, ValidacionError
from app.repositories.base import AbrirSesion, Fila
from app.services.calificacion import calificar
from app.services.ruta_service import RutaService, VerificadorCurso

VISIBLES_PARA_ESTUDIANTE = (EVALUACION_PUBLICADA, EVALUACION_CERRADA)


class RepositorioEvaluaciones(Protocol):
    def obtener(self, sesion: Any, evaluacion_id: int) -> Fila | None: ...
    def de_bloque(self, sesion: Any, bloque_id: int) -> Fila | None: ...
    def preguntas(self, sesion: Any, evaluacion_id: int, *, con_respuesta: bool) -> list[Fila]: ...
    def bloquear_intentos(self, sesion: Any, evaluacion_id: int, estudiante_id: str) -> None: ...
    def contar_intentos(self, sesion: Any, evaluacion_id: int, estudiante_id: str) -> int: ...
    def registrar_intento(self, sesion: Any, datos: Fila) -> Fila: ...
    def intentos(self, sesion: Any, evaluacion_id: int, estudiante_id: str) -> list[Fila]: ...


def _resumen_intentos(intentos: list[Fila], intentos_max: int | None) -> Fila:
    return {
        "intentos_realizados": len(intentos),
        "intentos_restantes": None
        if intentos_max is None
        else max(intentos_max - len(intentos), 0),
        "mejor_puntaje": max((i["puntaje"] for i in intentos), default=None),
        "aprobado": any(i["aprobado"] for i in intentos),
    }


class EvaluacionService:
    def __init__(
        self,
        abrir_sesion: AbrirSesion,
        evaluaciones: RepositorioEvaluaciones,
        cursos: VerificadorCurso,
        ruta: RutaService,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._evaluaciones = evaluaciones
        self._cursos = cursos
        self._ruta = ruta

    def obtener(self, evaluacion_id: int, estudiante_id: str) -> Fila:
        with self._abrir_sesion() as sesion:
            evaluacion = self._visible(sesion, evaluacion_id, estudiante_id)
            preguntas = self._evaluaciones.preguntas(sesion, evaluacion_id, con_respuesta=False)
            intentos = self._evaluaciones.intentos(sesion, evaluacion_id, estudiante_id)
        return {
            **evaluacion,
            "preguntas": preguntas,
            **_resumen_intentos(intentos, evaluacion["intentos_max"]),
        }

    def historial(self, evaluacion_id: int, estudiante_id: str) -> list[Fila]:
        """Del mas reciente al mas antiguo."""
        with self._abrir_sesion() as sesion:
            self._visible(sesion, evaluacion_id, estudiante_id)
            return self._evaluaciones.intentos(sesion, evaluacion_id, estudiante_id)

    def presentar(self, evaluacion_id: int, estudiante_id: str, respuestas: dict[str, int]) -> Fila:
        with self._abrir_sesion() as sesion:
            evaluacion = self._visible(sesion, evaluacion_id, estudiante_id)
            self._exigir_abierta(evaluacion)
            if evaluacion["bloque_id"] is not None and self._ruta.bloque_bloqueado(
                sesion, estudiante_id, evaluacion["curso_id"], evaluacion["bloque_id"]
            ):
                raise ReglaNegocio("Primero aprueba la evaluación del bloque anterior.")

            self._evaluaciones.bloquear_intentos(sesion, evaluacion_id, estudiante_id)
            maximo = evaluacion["intentos_max"]
            if maximo is not None and (
                self._evaluaciones.contar_intentos(sesion, evaluacion_id, estudiante_id) >= maximo
            ):
                raise ReglaNegocio(f"Ya usaste todos los intentos permitidos ({maximo}).")

            preguntas = self._evaluaciones.preguntas(sesion, evaluacion_id, con_respuesta=True)
            if not preguntas:
                raise ReglaNegocio("Esta evaluación todavía no tiene preguntas.")
            _exigir_preguntas_conocidas(preguntas, respuestas)

            resultado = calificar(preguntas, respuestas, evaluacion["porcentaje_aprobacion"])
            intento = self._evaluaciones.registrar_intento(
                sesion,
                {
                    "evaluacion_id": evaluacion_id,
                    "estudiante_id": estudiante_id,
                    "puntaje": resultado["puntaje"],
                    "correctas": resultado["correctas"],
                    "total": resultado["total"],
                    "aprobado": resultado["aprobado"],
                    "respuestas": respuestas,
                },
            )
        return {
            "id": intento["id"],
            "evaluacion_id": evaluacion_id,
            **resultado,
            "creado_en": intento["creado_en"],
        }

    def evaluacion_de_bloque(self, bloque_id: int) -> Fila | None:
        with self._abrir_sesion() as sesion:
            return self._evaluaciones.de_bloque(sesion, bloque_id)

    def preguntas_publicas(self, evaluacion_id: int) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            return self._evaluaciones.preguntas(sesion, evaluacion_id, con_respuesta=False)

    # --- Privados ---------------------------------------------------------------
    def _visible(self, sesion: Any, evaluacion_id: int, estudiante_id: str) -> Fila:
        """Borradores y evaluaciones de cursos ajenos responden 404 (no se revela que existen)."""
        evaluacion = self._evaluaciones.obtener(sesion, evaluacion_id)
        visible = evaluacion is not None and evaluacion["estado"] in VISIBLES_PARA_ESTUDIANTE
        if visible and evaluacion["curso_id"] is not None:
            visible = self._cursos.puede_ver(sesion, evaluacion["curso_id"], estudiante_id)
        if not visible:
            raise NoEncontrado(f"No existe la evaluación {evaluacion_id}")
        return evaluacion

    @staticmethod
    def _exigir_abierta(evaluacion: Fila) -> None:
        if evaluacion["estado"] == EVALUACION_CERRADA:
            raise ReglaNegocio("Esta evaluación ya está cerrada.")
        limite = evaluacion["fecha_limite"]
        if limite is not None and datetime.fromisoformat(limite) < datetime.now(UTC):
            raise ReglaNegocio("La fecha límite de esta evaluación ya pasó.")


def _exigir_preguntas_conocidas(preguntas: list[Fila], respuestas: dict[str, int]) -> None:
    validas = {str(p["id"]) for p in preguntas}
    ajenas = sorted(set(respuestas) - validas)
    if ajenas:
        raise ValidacionError(
            details=[
                {"campo": f"respuestas.{pid}", "mensaje": "No es una pregunta de esta evaluación."}
                for pid in ajenas
            ]
        )

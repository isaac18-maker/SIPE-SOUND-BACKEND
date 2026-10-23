# =========================================================
# Progreso del estudiante.
# - Lecciones y ejercicios: tablas con FK (progreso_lecciones / _ejercicios) por SQL.
# - Bloques: aprobados si hay un intento aprobado en su evaluacion (HU-B-308).
# =========================================================
from typing import Any, Protocol

from app.core.constants import TIPO_EJERCICIO, TIPO_LECCION
from app.core.errors import NoEncontrado
from app.core.security import CurrentUser
from app.repositories.base import (
    AbrirSesion,
    Fila,
    RepositorioProgresoContenido,
    VerificadorExistencia,
)
from app.schemas.progreso import AvanceEjercicioIn, AvanceIn


class LectorBloquesAprobados(Protocol):
    def bloques_aprobados(self, sesion: Any, estudiante_id: str) -> list[Fila]: ...


class ProgresoService:
    def __init__(
        self,
        abrir_sesion: AbrirSesion,
        progreso: RepositorioProgresoContenido,
        evaluaciones: LectorBloquesAprobados,
        lecciones: VerificadorExistencia,
        ejercicios: VerificadorExistencia,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._progreso = progreso
        self._evaluaciones = evaluaciones
        self._existe = {TIPO_LECCION: lecciones, TIPO_EJERCICIO: ejercicios}

    def registrar_leccion(self, usuario_id: str, leccion_id: int, avance: AvanceIn) -> Fila:
        """El avance nunca retrocede: porcentaje maximo y completado permanente."""
        self._exigir(TIPO_LECCION, leccion_id)
        with self._abrir_sesion() as sesion:
            return self._progreso.registrar_leccion(
                sesion,
                usuario_id,
                leccion_id,
                porcentaje=avance.porcentaje,
                completado=avance.completado,
            )

    def registrar_ejercicio(
        self, usuario_id: str, ejercicio_id: int, avance: AvanceEjercicioIn
    ) -> Fila:
        """Igual que las lecciones; ademas conserva el mejor BPM alcanzado."""
        self._exigir(TIPO_EJERCICIO, ejercicio_id)
        with self._abrir_sesion() as sesion:
            return self._progreso.registrar_ejercicio(
                sesion,
                usuario_id,
                ejercicio_id,
                porcentaje=avance.porcentaje,
                completado=avance.completado,
                mejor_bpm=avance.mejor_bpm,
            )

    def resumen(self, usuario: CurrentUser) -> dict[str, Any]:
        with self._abrir_sesion() as sesion:
            lecciones = self._progreso.listar_lecciones(sesion, usuario.id)
            ejercicios = self._progreso.listar_ejercicios(sesion, usuario.id)
            totales = self._progreso.totales_catalogo(sesion)
            bloques = self._evaluaciones.bloques_aprobados(sesion, usuario.id)
        fechas = [f["actualizado_en"] for f in (*lecciones, *ejercicios, *bloques)]
        return {
            "lecciones": {
                "completadas": sum(f["completado"] for f in lecciones),
                "total": totales["lecciones"],
            },
            "ejercicios": {
                "completados": sum(f["completado"] for f in ejercicios),
                "total": totales["ejercicios"],
            },
            "bloques_aprobados": len(bloques),
            "ultimo_avance": max(fechas) if fechas else None,
        }

    # --- Privados -----------------------------------------------------------
    def _exigir(self, tipo: str, contenido_id: int) -> None:
        if not self._existe[tipo].existe(contenido_id):
            raise NoEncontrado(f"No existe {tipo} con id {contenido_id}")

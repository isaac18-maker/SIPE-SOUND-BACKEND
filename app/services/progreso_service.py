# =========================================================
# Progreso del estudiante.
# - Lecciones y ejercicios: tablas con FK (progreso_lecciones / _ejercicios) por SQL.
# - Bloques (resultado de quizzes): siguen en la tabla `progreso` via Supabase
#   REST con el token del estudiante, hasta HU-B-308.
# GET/POST /progreso se mantienen con su forma anterior (adaptador _a_legado).
# =========================================================
from typing import Any

from app.core.constants import TIPO_BLOQUE, TIPO_EJERCICIO, TIPO_LECCION
from app.core.errors import NoEncontrado
from app.core.security import CurrentUser
from app.repositories.base import (
    AbrirSesion,
    Fila,
    RepositorioProgreso,
    RepositorioProgresoContenido,
    VerificadorExistencia,
)
from app.schemas.progreso import AvanceEjercicioIn, AvanceIn, ProgresoCreate

COLUMNA_CONTENIDO = {TIPO_LECCION: "leccion_id", TIPO_EJERCICIO: "ejercicio_id"}


def _a_legado(tipo: str, fila: Fila) -> Fila:
    """Forma de la antigua tabla `progreso` que espera el frontend actual."""
    contenido_id = fila[COLUMNA_CONTENIDO[tipo]]
    return {
        "id": f"{tipo}-{contenido_id}",
        "usuario_id": fila["estudiante_id"],
        "tipo": tipo,
        "contenido_id": contenido_id,
        "porcentaje": fila["porcentaje"],
        "completado": fila["completado"],
        "actualizado_en": fila["actualizado_en"],
    }


class ProgresoService:
    def __init__(
        self,
        abrir_sesion: AbrirSesion,
        progreso: RepositorioProgresoContenido,
        progreso_bloques: RepositorioProgreso,
        lecciones: VerificadorExistencia,
        ejercicios: VerificadorExistencia,
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._progreso = progreso
        self._progreso_bloques = progreso_bloques
        self._existe = {TIPO_LECCION: lecciones, TIPO_EJERCICIO: ejercicios}

    # --- API v1 -------------------------------------------------------------
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
        bloques = self._bloques(usuario)
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
            "bloques_aprobados": sum(bool(f.get("completado")) for f in bloques),
            "ultimo_avance": max(fechas) if fechas else None,
        }

    # --- Compatibilidad con GET/POST /progreso ------------------------------
    def listar(self, usuario: CurrentUser) -> list[Fila]:
        with self._abrir_sesion() as sesion:
            lecciones = self._progreso.listar_lecciones(sesion, usuario.id)
            ejercicios = self._progreso.listar_ejercicios(sesion, usuario.id)
        return [
            *(_a_legado(TIPO_LECCION, f) for f in lecciones),
            *(_a_legado(TIPO_EJERCICIO, f) for f in ejercicios),
            *self._bloques(usuario),
        ]

    def guardar(self, usuario: CurrentUser, datos: ProgresoCreate) -> list[Fila]:
        if datos.tipo == TIPO_LECCION:
            fila = self.registrar_leccion(
                usuario.id, datos.contenido_id, AvanceIn(**self._avance(datos))
            )
        else:
            fila = self.registrar_ejercicio(
                usuario.id, datos.contenido_id, AvanceEjercicioIn(**self._avance(datos))
            )
        return [_a_legado(datos.tipo, fila)]

    # --- Privados -----------------------------------------------------------
    def _exigir(self, tipo: str, contenido_id: int) -> None:
        if not self._existe[tipo].existe(contenido_id):
            raise NoEncontrado(f"No existe {tipo} con id {contenido_id}")

    def _bloques(self, usuario: CurrentUser) -> list[Fila]:
        filas = self._progreso_bloques.listar(usuario.id, usuario.token)
        return [f for f in filas if f["tipo"] == TIPO_BLOQUE]

    @staticmethod
    def _avance(datos: ProgresoCreate) -> dict[str, Any]:
        return {"porcentaje": datos.porcentaje, "completado": bool(datos.completado)}

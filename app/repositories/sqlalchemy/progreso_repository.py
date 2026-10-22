from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.ejercicio import Ejercicio
from app.models.leccion import Leccion
from app.models.progreso_contenido import ProgresoEjercicio, ProgresoLeccion
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import a_fila


class SqlProgresoRepository:
    """No abre ni confirma transacciones: usa la sesion del servicio."""

    def listar_lecciones(self, sesion: Session, estudiante_id: str) -> list[Fila]:
        consulta = select(ProgresoLeccion).where(ProgresoLeccion.estudiante_id == estudiante_id)
        return [a_fila(p) for p in sesion.scalars(consulta)]

    def listar_ejercicios(self, sesion: Session, estudiante_id: str) -> list[Fila]:
        consulta = select(ProgresoEjercicio).where(ProgresoEjercicio.estudiante_id == estudiante_id)
        return [a_fila(p) for p in sesion.scalars(consulta)]

    def registrar_leccion(
        self,
        sesion: Session,
        estudiante_id: str,
        leccion_id: int,
        *,
        porcentaje: int,
        completado: bool,
    ) -> Fila:
        nuevo = insert(ProgresoLeccion).values(
            estudiante_id=estudiante_id,
            leccion_id=leccion_id,
            porcentaje=porcentaje,
            completado=completado,
        )
        upsert = nuevo.on_conflict_do_update(
            index_elements=[ProgresoLeccion.estudiante_id, ProgresoLeccion.leccion_id],
            set_=_sin_retroceso(ProgresoLeccion, nuevo),
        )
        return _ejecutar(sesion, upsert, ProgresoLeccion)

    def registrar_ejercicio(
        self,
        sesion: Session,
        estudiante_id: str,
        ejercicio_id: int,
        *,
        porcentaje: int,
        completado: bool,
        mejor_bpm: int | None,
    ) -> Fila:
        nuevo = insert(ProgresoEjercicio).values(
            estudiante_id=estudiante_id,
            ejercicio_id=ejercicio_id,
            porcentaje=porcentaje,
            completado=completado,
            mejor_bpm=mejor_bpm,
        )
        cambios = _sin_retroceso(ProgresoEjercicio, nuevo)
        # greatest() ignora NULL: conserva el mejor BPM registrado.
        cambios["mejor_bpm"] = func.greatest(ProgresoEjercicio.mejor_bpm, nuevo.excluded.mejor_bpm)
        upsert = nuevo.on_conflict_do_update(
            index_elements=[ProgresoEjercicio.estudiante_id, ProgresoEjercicio.ejercicio_id],
            set_=cambios,
        )
        return _ejecutar(sesion, upsert, ProgresoEjercicio)

    def totales_catalogo(self, sesion: Session) -> dict[str, int]:
        return {
            "lecciones": sesion.scalar(select(func.count()).select_from(Leccion)) or 0,
            "ejercicios": sesion.scalar(select(func.count()).select_from(Ejercicio)) or 0,
        }


def _sin_retroceso(modelo, nuevo) -> dict:
    """Regla de negocio aplicada de forma atomica en el upsert: el avance nunca baja
    (porcentaje = el mayor registrado) y una vez completado sigue completado."""
    return {
        "porcentaje": func.greatest(modelo.porcentaje, nuevo.excluded.porcentaje),
        "completado": modelo.completado | nuevo.excluded.completado,
        "actualizado_en": func.now(),
    }


def _ejecutar(sesion: Session, upsert, modelo) -> Fila:
    fila = sesion.scalars(
        upsert.returning(modelo), execution_options={"populate_existing": True}
    ).one()
    return a_fila(fila)

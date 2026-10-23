from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.constants import ESTADO_PUBLICADO, ZONA_HORARIA
from app.models.ejercicio import Ejercicio
from app.models.leccion import Leccion
from app.models.progreso_contenido import ProgresoEjercicio, ProgresoLeccion
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import a_fila, formatear_fecha


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
        """Solo lo publicado: los borradores del panel docente no cuentan (HU-B-309)."""
        lecciones = select(func.count()).where(Leccion.estado == ESTADO_PUBLICADO)
        ejercicios = select(func.count()).where(Ejercicio.estado == ESTADO_PUBLICADO)
        return {
            "lecciones": sesion.scalar(lecciones) or 0,
            "ejercicios": sesion.scalar(ejercicios) or 0,
        }

    def actividad(
        self, sesion: Session, estudiante_id: str, *, dias: int, limite: int
    ) -> dict[str, list[Fila]]:
        """Eventos recientes (lecciones, ejercicios e intentos) y registros por dia en la
        zona del proyecto, con los dias vacios incluidos. Dos sentencias, sin N+1."""
        parametros = {
            "estudiante": estudiante_id,
            "dias": dias,
            "limite": limite,
            "zona": ZONA_HORARIA,
        }
        recientes = [
            {**dict(f._mapping), "fecha": formatear_fecha(f.fecha)}
            for f in sesion.execute(text(RECIENTES), parametros)
        ]
        por_dia = [
            {"fecha": f.fecha.isoformat(), "registros": f.registros}
            for f in sesion.execute(text(POR_DIA), parametros)
        ]
        return {"recientes": recientes, "por_dia": por_dia}


# Un evento por registro de avance: el progreso guarda solo la ultima fecha de cada
# contenido (actualizado_en); cada intento de evaluacion es un evento propio.
CTE_EVENTOS = """
eventos as (
  select 'leccion' as tipo, l.id, l.titulo, l.bloque_id, p.actualizado_en as fecha,
         p.completado, null::int as mejor_bpm, null::int as puntaje, null::boolean as aprobado
  from public.progreso_lecciones p join public.lecciones l on l.id = p.leccion_id
  where p.estudiante_id = :estudiante
  union all
  select 'ejercicio', e.id, e.nombre, l.bloque_id, p.actualizado_en,
         p.completado, p.mejor_bpm, null, null
  from public.progreso_ejercicios p join public.ejercicios e on e.id = p.ejercicio_id
  left join public.lecciones l on l.id = e.leccion_id
  where p.estudiante_id = :estudiante
  union all
  select 'evaluacion', ev.id, ev.titulo, ev.bloque_id, i.creado_en,
         null, null, i.puntaje, i.aprobado
  from public.intentos_evaluacion i join public.evaluaciones ev on ev.id = i.evaluacion_id
  where i.estudiante_id = :estudiante
)"""

RECIENTES = f"""
with {CTE_EVENTOS}
select * from eventos order by fecha desc limit :limite
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

POR_DIA = f"""
with {CTE_EVENTOS},
hoy as (select (now() at time zone :zona)::date as dia)
select d::date as fecha, count(e.tipo) as registros
from hoy, generate_series(hoy.dia - (:dias - 1), hoy.dia, interval '1 day') as d
left join eventos e on (e.fecha at time zone :zona)::date = d::date
group by d order by d
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros


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

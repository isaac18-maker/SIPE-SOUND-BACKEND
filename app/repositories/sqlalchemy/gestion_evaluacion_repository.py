# =========================================================
# Gestion de evaluaciones desde el panel (HU-B-311). Resultados en
# consultas agregadas fijas (sin N+1). Usa la sesion del servicio.
# =========================================================
from typing import Any

from sqlalchemy import delete, exists, func, insert, select, text, update
from sqlalchemy.orm import Session

from app.models.curso import Curso
from app.models.evaluacion import Evaluacion, IntentoEvaluacion, PreguntaEvaluacion
from app.repositories.base import Fila
from app.repositories.sqlalchemy._comun import a_fila, formatear_fecha

# Mejor intento de cada estudiante (mayor puntaje; ante empate, el mas reciente).
CTE_MEJORES = """
mejores as (
  select distinct on (it.estudiante_id) it.estudiante_id, it.puntaje, it.respuestas
  from public.intentos_evaluacion it
  where it.evaluacion_id = :evaluacion_id
  order by it.estudiante_id, it.puntaje desc, it.creado_en desc
)"""

CIFRAS = f"""
with {CTE_MEJORES}
select
  (select count(*) from public.intentos_evaluacion where evaluacion_id = :evaluacion_id)
    as intentos,
  (select count(*) from mejores) as estudiantes_que_presentaron,
  (select round(avg(puntaje)) from mejores) as promedio_mejor_puntaje,
  (select count(*) from public.intentos_evaluacion
    where evaluacion_id = :evaluacion_id and aprobado) as intentos_aprobados,
  (select count(distinct estudiante_id) from public.intentos_evaluacion
    where evaluacion_id = :evaluacion_id and aprobado) as estudiantes_aprobados,
  (select count(*) from public.inscripciones where curso_id = :curso_id)
    as estudiantes_del_curso
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

PREGUNTAS = f"""
with {CTE_MEJORES}
select p.id, p.orden, p.enunciado,
  case when (select count(*) from mejores) = 0 then null
       else round(100.0 * count(m.estudiante_id) filter (
              where (m.respuestas ->> p.id::text)::int = p.respuesta_correcta)
            / (select count(*) from mejores)) end as aciertos_pct
from public.preguntas_evaluacion p
left join mejores m on true
where p.evaluacion_id = :evaluacion_id
group by p.id
order by aciertos_pct asc nulls last, p.orden
"""  # noqa: S608 - solo fragmentos constantes; los datos van como parametros

ESTUDIANTES = """
select it.estudiante_id, pr.nombre, max(it.puntaje) as mejor_puntaje,
       count(*) as intentos, bool_or(it.aprobado) as aprobado,
       max(it.creado_en) as ultimo_intento
from public.intentos_evaluacion it
join public.profiles pr on pr.id = it.estudiante_id
where it.evaluacion_id = :evaluacion_id
group by it.estudiante_id, pr.nombre
order by mejor_puntaje desc, pr.nombre
"""

SIN_PRESENTAR = """
select i.estudiante_id, pr.nombre
from public.inscripciones i
join public.profiles pr on pr.id = i.estudiante_id
where i.curso_id = :curso_id
  and not exists (
    select 1 from public.intentos_evaluacion it
    where it.evaluacion_id = :evaluacion_id and it.estudiante_id = i.estudiante_id)
order by pr.nombre
"""


def _filas(sesion: Session, sql: str, parametros: dict[str, Any]) -> list[Fila]:
    return [
        {k: formatear_fecha(v) if hasattr(v, "isoformat") else v for k, v in f._mapping.items()}
        for f in sesion.execute(text(sql), parametros)
    ]


class SqlGestionEvaluacionRepository:
    def listar(
        self,
        sesion: Session,
        *,
        docente_id: str | None,
        curso_id: int | None,
        estado: str | None,
    ) -> list[Fila]:
        """docente_id None = admin (incluye las globales de bloque)."""
        preguntas = (
            select(func.count())
            .where(PreguntaEvaluacion.evaluacion_id == Evaluacion.id)
            .correlate(Evaluacion)
            .scalar_subquery()
        )
        consulta = select(Evaluacion, preguntas.label("preguntas"))
        if docente_id is not None:
            propios = select(Curso.id).where(Curso.docente_id == docente_id)
            consulta = consulta.where(Evaluacion.curso_id.in_(propios))
        if curso_id is not None:
            consulta = consulta.where(Evaluacion.curso_id == curso_id)
        if estado is not None:
            consulta = consulta.where(Evaluacion.estado == estado)
        return [
            {**a_fila(f.Evaluacion), "preguntas": f.preguntas}
            for f in sesion.execute(consulta.order_by(Evaluacion.creado_en.desc()))
        ]

    def obtener(
        self, sesion: Session, evaluacion_id: int, *, bloquear: bool = False
    ) -> Fila | None:
        fila = sesion.get(Evaluacion, evaluacion_id, with_for_update=bloquear)
        return a_fila(fila) if fila else None

    def preguntas(self, sesion: Session, evaluacion_id: int) -> list[Fila]:
        """Con la respuesta correcta: solo para el panel docente."""
        consulta = (
            select(PreguntaEvaluacion)
            .where(PreguntaEvaluacion.evaluacion_id == evaluacion_id)
            .order_by(PreguntaEvaluacion.orden)
        )
        return [a_fila(p) for p in sesion.scalars(consulta)]

    def crear(self, sesion: Session, datos: Fila) -> Fila:
        fila = sesion.scalars(insert(Evaluacion).values(**datos).returning(Evaluacion)).one()
        return a_fila(fila)

    def actualizar(self, sesion: Session, evaluacion_id: int, cambios: Fila) -> Fila:
        fila = sesion.scalars(
            update(Evaluacion)
            .where(Evaluacion.id == evaluacion_id)
            .values(**cambios)
            .returning(Evaluacion),
            execution_options={"populate_existing": True},
        ).one()
        return a_fila(fila)

    def tiene_intentos(self, sesion: Session, evaluacion_id: int) -> bool:
        condicion = exists().where(IntentoEvaluacion.evaluacion_id == evaluacion_id)
        return bool(sesion.scalar(select(condicion)))

    def contar_preguntas(self, sesion: Session, evaluacion_id: int) -> int:
        consulta = select(func.count()).where(PreguntaEvaluacion.evaluacion_id == evaluacion_id)
        return sesion.scalar(consulta) or 0

    def reemplazar_preguntas(
        self, sesion: Session, evaluacion_id: int, preguntas: list[Fila]
    ) -> list[Fila]:
        sesion.execute(
            delete(PreguntaEvaluacion).where(PreguntaEvaluacion.evaluacion_id == evaluacion_id)
        )
        sesion.execute(
            insert(PreguntaEvaluacion),
            [
                {**p, "evaluacion_id": evaluacion_id, "orden": orden}
                for orden, p in enumerate(preguntas, start=1)
            ],
        )
        return self.preguntas(sesion, evaluacion_id)

    def eliminar(self, sesion: Session, evaluacion_id: int) -> None:
        sesion.execute(delete(Evaluacion).where(Evaluacion.id == evaluacion_id))

    def resultados(self, sesion: Session, evaluacion: Fila) -> Fila:
        parametros = {"evaluacion_id": evaluacion["id"], "curso_id": evaluacion["curso_id"]}
        cifras = _filas(sesion, CIFRAS, parametros)[0]
        sin_presentar = _filas(sesion, SIN_PRESENTAR, parametros) if evaluacion["curso_id"] else []
        return {
            "cifras": cifras,
            "preguntas": _filas(sesion, PREGUNTAS, parametros),
            "estudiantes": _filas(sesion, ESTUDIANTES, parametros),
            "sin_presentar": sin_presentar,
        }

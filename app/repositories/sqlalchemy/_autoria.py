# =========================================================
# Autoria y alcance del contenido por docente (HU-B-412).
# - alcance: lo que un docente puede ver y editar ademas de lo suyo es el contenido de los bloques
#   que recorren SUS cursos activos (la ruta propia del curso o, si no definio la suya, la global,
#   la misma regla de la ruta del estudiante).
# - nombres: quien creo y quien modifico por ultima vez, como texto (nunca el correo).
# =========================================================
from typing import Any

from sqlalchemy import ColumnElement, exists, literal, or_, select
from sqlalchemy.orm import Session

from app.core.constants import ESTADO_PUBLICADO
from app.models.bloque import Bloque
from app.models.curso import Curso
from app.models.curso_bloque import CursoBloque
from app.models.ejercicio import Ejercicio
from app.models.leccion import Leccion
from app.models.profile import Profile
from app.repositories.base import Fila


def condicion_de_bloque(columna: Any, docente_id: str) -> ColumnElement[bool]:
    """`columna` (un bloque_id) esta en la ruta de algun curso activo del docente."""
    activos = (Curso.docente_id == docente_id) & Curso.archivado_en.is_(None)
    con_ruta_propia = select(CursoBloque.bloque_id).where(
        CursoBloque.curso_id.in_(select(Curso.id).where(activos))
    )
    # Un curso sin ruta propia recorre todos los bloques publicados.
    curso_sin_ruta = exists().where(
        activos, ~exists().where(CursoBloque.curso_id == Curso.id).correlate(Curso)
    )
    publicados = select(Bloque.id).where(Bloque.estado == ESTADO_PUBLICADO, curso_sin_ruta)
    return or_(columna.in_(con_ruta_propia), columna.in_(publicados))


def referencia_de_leccion(datos: Fila, docente_id: str) -> ColumnElement[bool]:
    """Un bloque_id recibido (aun sin fila) esta en la ruta de un curso activo del docente."""
    return condicion_de_bloque(literal(datos["bloque_id"]), docente_id)


def referencia_de_ejercicio(datos: Fila, docente_id: str) -> ColumnElement[bool]:
    """Un leccion_id recibido pertenece a un bloque de la ruta de un curso activo del docente."""
    lecciones = select(Leccion.id).where(condicion_de_bloque(Leccion.bloque_id, docente_id))
    return literal(datos["leccion_id"]).in_(lecciones)


def alcance_de_lecciones(docente_id: str) -> ColumnElement[bool]:
    return condicion_de_bloque(Leccion.bloque_id, docente_id)


def alcance_de_ejercicios(docente_id: str) -> ColumnElement[bool]:
    lecciones = select(Leccion.id).where(condicion_de_bloque(Leccion.bloque_id, docente_id))
    return Ejercicio.leccion_id.in_(lecciones)


def _nombre(nombre: str | None, apellido: str | None) -> str | None:
    return " ".join(p for p in (nombre, apellido) if p) if nombre else None


def con_nombres(sesion: Session, filas: list[Fila]) -> list[Fila]:
    """Agrega `autor` y `modificado_por` (nombre o None) en una consulta."""
    ids = {f[c] for f in filas for c in ("autor_id", "actualizado_por") if f.get(c)}
    perfiles = {}
    if ids:
        consulta = select(Profile.id, Profile.nombre, Profile.apellido).where(Profile.id.in_(ids))
        perfiles = {p.id: _nombre(p.nombre, p.apellido) for p in sesion.execute(consulta)}
    return [
        {
            **f,
            "autor": perfiles.get(f.get("autor_id")),
            "modificado_por": perfiles.get(f.get("actualizado_por")),
        }
        for f in filas
    ]

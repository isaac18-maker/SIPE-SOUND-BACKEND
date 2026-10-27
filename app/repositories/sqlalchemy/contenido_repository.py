# =========================================================
# Repositorio generico del contenido editable (lecciones, ejercicios y
# bloques, HU-B-309): una sola implementacion parametrizada por modelo.
# No abre ni confirma transacciones: usa la sesion del servicio.
# =========================================================
from collections.abc import Callable
from typing import Any

from sqlalchemy import ColumnElement, delete, exists, func, insert, select, update
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.core.constants import ESTADO_ARCHIVADO
from app.models.acorde import Acorde
from app.models.base import Base
from app.models.bloque import Bloque
from app.models.leccion import Leccion
from app.repositories.base import Fila
from app.repositories.sqlalchemy._autoria import con_nombres
from app.repositories.sqlalchemy._comun import a_fila

# Recibe el id y devuelve la condicion "esta en uso" (progreso o dependientes).
CondicionUso = Callable[[Any], ColumnElement[bool]]


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlContenidoRepository:
    def __init__(
        self,
        modelo: type[Base],
        *,
        columna_texto: InstrumentedAttribute,
        filtros: tuple[str, ...],
        en_uso: CondicionUso,
        alcance: Callable[[str], ColumnElement[bool]] | None = None,
        referencia: Callable[[Fila, str], ColumnElement[bool]] | None = None,
    ) -> None:
        """alcance: dado un docente, la condicion de lo que puede gestionar aunque no sea suyo
        (contenido de los bloques de sus cursos, HU-B-412). Sin ella, solo lo propio.
        referencia: dados los datos de un contenido NUEVO y un docente, si lo que referencia (el
        bloque o la leccion) esta en el alcance del docente (HU-B-417)."""
        self._modelo = modelo
        self._texto = columna_texto
        self._filtros = filtros
        self._en_uso = en_uso
        self._alcance = alcance
        self._referencia = referencia
        self._con_archivado = hasattr(modelo, "archivado_en")

    def listar(
        self,
        sesion: Session,
        filtros: dict[str, Any],
        *,
        autor_id: str | None,
        pagina: int,
        por_pagina: int,
    ) -> tuple[list[Fila], int]:
        m = self._modelo
        consulta = select(m)
        for campo in self._filtros:
            if filtros.get(campo) is not None:
                consulta = consulta.where(getattr(m, campo) == filtros[campo])
        if filtros.get("q"):
            consulta = consulta.where(
                self._texto.ilike(f"%{_escapar_like(filtros['q'])}%", escape="\\")
            )
        if autor_id is not None:
            propio = m.autor_id == autor_id
            consulta = consulta.where(propio | self._alcance(autor_id) if self._alcance else propio)
        total = sesion.scalar(select(func.count()).select_from(consulta.subquery())) or 0
        pagina_actual = (
            consulta.order_by(m.actualizado_en.desc(), m.id.desc())
            .offset((pagina - 1) * por_pagina)
            .limit(por_pagina)
        )
        filas = [a_fila(f) for f in sesion.scalars(pagina_actual)]
        return con_nombres(sesion, filas), total

    def obtener(self, sesion: Session, contenido_id: int, *, bloquear: bool = False) -> Fila | None:
        fila = sesion.get(self._modelo, contenido_id, with_for_update=bloquear)
        return con_nombres(sesion, [a_fila(fila)])[0] if fila else None

    def en_alcance_de(self, sesion: Session, contenido_id: int, docente_id: str) -> bool:
        """Esta en la ruta de un curso activo del docente (aunque lo haya creado otra persona)."""
        if self._alcance is None:
            return False
        consulta = select(
            exists().where(self._modelo.id == contenido_id, self._alcance(docente_id))
        )
        return bool(sesion.scalar(consulta))

    def referencia_en_alcance_de(self, sesion: Session, datos: Fila, docente_id: str) -> bool:
        """Lo que el contenido nuevo referencia esta en un curso activo del docente."""
        if self._referencia is None:
            return False
        return bool(sesion.scalar(select(self._referencia(datos, docente_id))))

    def crear(self, sesion: Session, datos: Fila) -> Fila:
        fila = sesion.scalars(insert(self._modelo).values(**datos).returning(self._modelo)).one()
        return con_nombres(sesion, [a_fila(fila)])[0]

    def actualizar(self, sesion: Session, contenido_id: int, cambios: Fila) -> Fila:
        fila = sesion.scalars(
            update(self._modelo)
            .where(self._modelo.id == contenido_id)
            .values(**cambios)
            .returning(self._modelo),
            execution_options={"populate_existing": True},
        ).one()
        return con_nombres(sesion, [a_fila(fila)])[0]

    def cambiar_estado(self, sesion: Session, contenido_id: int, estado: str) -> Fila:
        cambios: dict[str, Any] = {"estado": estado}
        if self._con_archivado:
            cambios["archivado_en"] = func.now() if estado == ESTADO_ARCHIVADO else None
        return self.actualizar(sesion, contenido_id, cambios)

    def en_uso(self, sesion: Session, contenido_id: int) -> bool:
        return bool(sesion.scalar(select(self._en_uso(contenido_id))))

    def eliminar(self, sesion: Session, contenido_id: int) -> None:
        sesion.execute(delete(self._modelo).where(self._modelo.id == contenido_id))


class SqlCatalogoRepository:
    """Verifica que existan las referencias del contenido (bloque, leccion, acordes)."""

    MODELOS = {"bloques": Bloque, "lecciones": Leccion}

    def existe(self, sesion: Session, tabla: str, ident: int) -> bool:
        modelo = self.MODELOS[tabla]
        return bool(sesion.scalar(select(exists().where(modelo.id == ident))))

    def acordes_faltantes(self, sesion: Session, nombres: list[str]) -> list[str]:
        existentes = set(sesion.scalars(select(Acorde.nombre).where(Acorde.nombre.in_(nombres))))
        return [n for n in nombres if n not in existentes]

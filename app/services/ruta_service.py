# =========================================================
# Ruta de aprendizaje (HU-B-308). UNICA implementacion de la regla de
# desbloqueo para todo el sistema (ruta del estudiante, evaluaciones y
# panel docente):
#   - el primer bloque de la ruta esta disponible;
#   - un bloque se desbloquea si el anterior esta aprobado o si el anterior
#     no tiene evaluacion (no hay nada que aprobar);
#   - "aprobado" = algun intento aprobado en la evaluacion global del bloque.
# =========================================================
from typing import Any, Protocol

from app.core.constants import (
    ACORDES_POR_BLOQUE,
    BLOQUE_APROBADO,
    BLOQUE_BLOQUEADO,
    BLOQUE_DISPONIBLE,
)
from app.core.errors import NoAutenticado, NoEncontrado
from app.repositories.base import AbrirSesion, Fila


class RepositorioRuta(Protocol):
    def bloques(self, sesion: Any, curso_id: int | None) -> list[Fila]: ...
    def lecciones(
        self, sesion: Any, bloque_ids: list[int], estudiante_id: str | None
    ) -> list[Fila]: ...
    def evaluaciones_de_bloques(self, sesion: Any, bloque_ids: list[int]) -> dict[int, int]: ...
    def desempeno(
        self, sesion: Any, bloque_ids: list[int], estudiante_id: str
    ) -> dict[int, Fila]: ...


class VerificadorCurso(Protocol):
    def puede_ver(self, sesion: Any, curso_id: int, usuario_id: str) -> bool: ...


def estados_de_bloques(
    bloque_ids: list[int], con_evaluacion: set[int], aprobados: set[int]
) -> dict[int, str]:
    """Funcion pura con la regla de desbloqueo."""
    estados: dict[int, str] = {}
    desbloqueado = True
    for bloque_id in bloque_ids:
        if bloque_id in aprobados:
            estados[bloque_id] = BLOQUE_APROBADO
        else:
            estados[bloque_id] = BLOQUE_DISPONIBLE if desbloqueado else BLOQUE_BLOQUEADO
        superado = bloque_id in aprobados or bloque_id not in con_evaluacion
        desbloqueado = desbloqueado and superado
    return estados


def acordes_del_bloque(lecciones: list[Fila]) -> list[str]:
    """Funcion pura: acordes distintos de las lecciones, en orden de leccion (HU-B-324)."""
    vistos: dict[str, None] = {}
    for leccion in lecciones:
        for acorde in leccion.get("acordes") or []:
            vistos.setdefault(acorde)
    return list(vistos)[:ACORDES_POR_BLOQUE]


class RutaService:
    def __init__(
        self, abrir_sesion: AbrirSesion, ruta: RepositorioRuta, cursos: VerificadorCurso
    ) -> None:
        self._abrir_sesion = abrir_sesion
        self._ruta = ruta
        self._cursos = cursos

    def ruta(self, usuario_id: str | None, curso_id: int | None) -> list[Fila]:
        """Sin sesion: todos los bloques disponibles y sin puntajes."""
        with self._abrir_sesion() as sesion:
            return self.ruta_en_sesion(sesion, usuario_id, curso_id)

    def ruta_en_sesion(self, sesion: Any, usuario_id: str | None, curso_id: int | None) -> list:
        if curso_id is not None:
            if usuario_id is None:
                raise NoAutenticado("Inicia sesión para ver la ruta de tu curso.")
            if not self._cursos.puede_ver(sesion, curso_id, usuario_id):
                raise NoEncontrado(f"No existe el curso {curso_id}")
        return self.ruta_de_estudiante(sesion, usuario_id, curso_id)

    def ruta_de_estudiante(
        self, sesion: Any, usuario_id: str | None, curso_id: int | None
    ) -> list[Fila]:
        """Sin verificar acceso: para quien ya lo verifico (p. ej. el docente del curso)."""
        bloques = self._ruta.bloques(sesion, curso_id)
        ids = [b["id"] for b in bloques]
        evaluaciones = self._ruta.evaluaciones_de_bloques(sesion, ids)
        lecciones = self._ruta.lecciones(sesion, ids, usuario_id)
        desempeno = self._ruta.desempeno(sesion, ids, usuario_id) if usuario_id else {}

        por_bloque: dict[int, list[Fila]] = {i: [] for i in ids}
        for leccion in lecciones:
            por_bloque[leccion["bloque_id"]].append(leccion)
        aprobados = {b for b, d in desempeno.items() if d["aprobado"]}
        estados = (
            estados_de_bloques(ids, set(evaluaciones), aprobados)
            if usuario_id
            else dict.fromkeys(ids, BLOQUE_DISPONIBLE)
        )
        return [
            {
                **bloque,
                "orden": posicion,
                "estado": estados[bloque["id"]],
                "evaluacion_id": evaluaciones.get(bloque["id"]),
                "mejor_puntaje": desempeno.get(bloque["id"], {}).get("mejor_puntaje"),
                "acordes": acordes_del_bloque(por_bloque[bloque["id"]]),
                "lecciones": [
                    {k: v for k, v in leccion.items() if k not in ("bloque_id", "acordes")}
                    for leccion in por_bloque[bloque["id"]]
                ],
            }
            for posicion, bloque in enumerate(bloques, start=1)
        ]

    def bloque_bloqueado(
        self, sesion: Any, usuario_id: str, curso_id: int | None, bloque_id: int
    ) -> bool:
        """True solo si el bloque esta en la ruta y aun no se desbloquea."""
        ruta = self.ruta_en_sesion(sesion, usuario_id, curso_id)
        return any(b["id"] == bloque_id and b["estado"] == BLOQUE_BLOQUEADO for b in ruta)
